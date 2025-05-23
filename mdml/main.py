import mdtraj as md
import os
import numpy as np
import pandas as pd
from pathlib import Path
import pickle
import msmbuilder
from msmbuilder.dataset import dataset
from msmbuilder.featurizer import DihedralFeaturizer
from msmbuilder import cluster
from Bio import PDB
from sklearn.svm import LinearSVC
import sksfa
import re
import math
import random

class TrajProcessor():

    def __init__(self):
        self.dataset : dataset = None
        self.topology : md.Trajectory = None
        self.residue_selection : str = None
        self.sincos : bool = False
        self.nosincos : bool = False
        self.featurizer : DihedralFeaturizer = None
        self.featurized_top : pd.DataFrame = None
        self.trajectory_lengths : list(int) = None
        self.diheds : list(np.ndarray) = None
        self.featurizer_nosincos : DihedralFeaturizer = None
        self.featurized_top_nosincos : pd.DataFrame = None
        self.diheds_nosincos : list(np.ndarray) = None
        self.W = None
        self.fxx = None
        self.res = None
        self.num_components : int = None

    def load_trajectories(self, path_to_trajectories : Path, topology_file : Path, stride : int = 1, atom_indices : str = None):
        try:
            self.residue_selection = atom_indices
            self.topology = md.load(topology_file)
            selection = self.topology.topology.select(atom_indices)
            self.topology = md.load(topology_file, atom_indices = selection)
            xtc_files = str(path_to_trajectories) + "/*.xtc"
            self.dataset = dataset(path=xtc_files,fmt='mdtraj',topology=topology_file, stride=stride, atom_indices=selection)
            self.trajectory_lengths = [self.dataset[i].n_frames for i in range(len(self.dataset))]
        except Exception as e:
            print(f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}")

    def featurize(self, types : list(), sincos : bool = True):
        if sincos:
            self.sincos = True
            self.featurizer = DihedralFeaturizer(types=types, sincos=sincos)
            self.featurized_top = pd.DataFrame(self.featurizer.describe_features(self.topology))
            self.diheds = self.featurizer.fit_transform(self.dataset)
        else:
            self.nosincos = True
            self.featurizer_nosincos = DihedralFeaturizer(types=types, sincos=False)
            self.featurized_top_nosincos = pd.DataFrame(self.featurizer_nosincos.describe_features(self.topology))
            self.diheds_nosincos = self.featurizer_nosincos.fit_transform(self.dataset)

    def describe_features(self, sincos : bool = True):
        if sincos and self.sincos:
            print(self.featurized_top)
        elif not(sincos) and self.nosincos:
            print(self.featurized_top_nosincos)

    def dump_description(self, description_file_path : str, sincos : bool = True):
        if sincos and self.sincos:
            with open(description_file_path, 'wb') as pickle_file:
                pickle.dump(self.featurized_top, pickle_file)
        elif not(sincos) and self.nosincos:
            with open(description_file_path, 'wb') as pickle_file:
                pickle.dump(self.featurized_top_nosincos, pickle_file)

    def dump_featurized(self, dump_file_path : str, sincos : bool = True):
        if sincos and self.sincos:
            with open(dump_file_path, 'wb') as pickle_file:
                pickle.dump(self.diheds, pickle_file)
        elif not(sincos) and self.nosincos:
            with open(dump_file_path, 'wb') as pickle_file:
                pickle.dump(self.diheds_nosincos, pickle_file)  

    def run_sfa(self, n_components : int = 2, tau : int = 1):
        if self.sincos:
            self.fxx=np.concatenate(self.diheds)
            self.num_components = n_components
            sfa = sksfa.SFA(n_components=n_components)
            sfa.fit(self.fxx, tau=tau)
            self.res = sfa.transform(self.fxx)
            self.W, b = sfa.affine_parameters()
            for i in range(1, len(self.W) + 1):
                component_col = 'sfa-' + str(i)
                self.featurized_top[component_col] = self.W[i - 1]
            means = []
            for i in range(self.fxx.shape[1]):
                means.append(np.mean(self.fxx[i]))
            self.featurized_top['means'] = means

    def create_plumed_file(self, plumed_filename):
        plumed = open(plumed_filename, "w")

        for index, row in self.featurized_top.iterrows():
            if row['otherinfo'] == "sin":
                feat_name = row['featuregroup'] + "-" + str(row['resseqs'][0])
                feat_label = row['featuregroup'] + "_" + str(row['resseqs'][0])
                plumed.write("TORSION ATOMS=@" + feat_name + " LABEL=" + feat_label + "\n")

        plumed.write("\n")

        ARG = "ARG="

        PERIODIC = "PERIODIC=NO"

        for index, row in self.featurized_top.iterrows():
            feat_label = row['featuregroup'] + "_" + str(row['resseqs'][0])
            MATHEVAL_ARG = "MATHEVAL ARG=" + feat_label
            FUNC = "FUNC=" + row['otherinfo'] + "(x)-" + str(row['means'])
            LABEL = "LABEL=meanfree_" + row['otherinfo'] + "_" + feat_label
            ARG += "meanfree_" + row['otherinfo'] + "_" + feat_label + "," if index != (len(self.featurized_top) - 1) else "meanfree_" + row['otherinfo'] + "_" + feat_label
            plumed.write(MATHEVAL_ARG + " " + FUNC + " " + LABEL + " " + PERIODIC + "\n")
        
        plumed.write("\n")

        for i in range(self.num_components):
            sfa_name = 'sfa-' + str(i + 1)
            COMBINE_LABEL = "COMBINE LABEL=sf" + str(i + 1)
            COEFFICIENTS = "COEFFICIENTS="
            for index, row in self.featurized_top.iterrows():
                COEFFICIENTS += str(row[sfa_name]) + "," if index != (len(self.featurized_top) - 1) else str(row[sfa_name])
            plumed.write(COMBINE_LABEL + "\n")
            plumed.write(ARG + "\n")
            plumed.write(COEFFICIENTS + " " + PERIODIC + "\n")
            plumed.write("\n")

    def dump_sfa_components(self, save_file : str):
        with open(save_file, 'wb') as f:
            pickle.dump(self.res, f)
        #pickle.dump(self.res, save_file)

    def cluster(self, method : str = 'kmeans', n_clusters = None):
        split_res = []
        i = 0
        for traj_length in self.trajectory_lengths:
            split_res.append(self.res[i:i + traj_length])
            i += traj_length
        if method == 'kmeans':
            clusterer = cluster.KMeans(n_clusters=n_clusters)
            self.clustered_trajs = clusterer.fit_transform(split_res)
        elif method == 'kcenters':
            clusterer = cluster.KCenters(n_clusters=n_clusters)
            self.clustered_trajs = clusterer.fit_transform(split_res)
        elif method == 'gmm':
            clusterer = cluster.GMM()
            self.clustered_trajs = clusterer.fit_transform(split_res)

    def dump_clusters(self, num_samples : int):
        cluster_dict = {}
        for traj_num, traj in enumerate(self.clustered_trajs):
            for frame_num, cluster_id in enumerate(traj):
                if cluster_id not in cluster_dict:
                    cluster_dict[cluster_id] = []
                cluster_dict[cluster_id].append((traj_num, frame_num))

        if not os.path.exists(f"./Clusters"):
            os.makedirs(f"./Clusters")            
        for cluster_num, frames in cluster_dict.items():
            try:
                sampled_frames = random.sample(frames, num_samples)
            except:
                sampled_frames = random.sample(frames, len(frames))    
            for traj_num, frame_num in sampled_frames:
                traj = self.dataset[traj_num]
                frame = traj[frame_num]
                frame.save(f"./Clusters/cluster{cluster_num}-run{traj_num}-frame{frame_num}.pdb")

        
    def classify(self, ensemble_one_path : str, ensemble_two_path : str, featurized_df_path : str):
        e1 = msmbuilder.utils.load(ensemble_one_path)
        e2 = msmbuilder.utils.load(ensemble_two_path)
        e1_xx = np.concatenate(e1)
        e2_xx = np.concatenate(e2)
        if e1_xx.shape != e2_xx.shape:
            raise ValueError("Ensembles must have the same number of features")
        combined_xx = [e1_xx, e2_xx]
        train_X = np.vstack(combined_xx)
        train_Y=np.concatenate([np.zeros(len(combined_xx[0])),np.ones(len(combined_xx[0]))])
        clf = LinearSVC(penalty="l2",C=1,dual=False)
        clf.fit(train_X, train_Y)
        self.classifier_features_and_weights = pd.DataFrame(pickle.load(open(featurized_df_path, 'rb')))
        classifier_weights = clf.coef_.T
        self.classifier_features_and_weights['weights'] = classifier_weights

    def classifier_plumed(self, plumed_filename : str):
        plumed = open(plumed_filename, "w")

        for index, row in self.classifier_features_and_weights.iterrows():
            if row['otherinfo'] == "sin":
                feat_name = row['featuregroup'] + "-" + str(row['resseqs'][0])
                feat_label = row['featuregroup'] + "_" + str(row['resseqs'][0])
                plumed.write("TORSION ATOMS=@" + feat_name + " LABEL=" + feat_label + "\n")
                #ARG += feat_label + "," if index != (len(self.classifier_features_and_weights) - 1) else feat_label

        plumed.write("\n")

        ARG = "ARG="

        PERIODIC = "PERIODIC=NO"

        for index, row in self.classifier_features_and_weights.iterrows():
            feat_label = row['featuregroup'] + "_" + str(row['resseqs'][0])
            MATHEVAL_ARG = "MATHEVAL ARG=" + feat_label
            FUNC = "FUNC=" + row['otherinfo'] + "(x)" 
            LABEL = "LABEL=" + row['otherinfo'] + "_" + feat_label
            ARG += row['otherinfo'] + "_" + feat_label + "," if index != (len(self.classifier_features_and_weights) - 1) else row['otherinfo'] + "_" + feat_label
            plumed.write(MATHEVAL_ARG + " " + FUNC + " " + LABEL + " " + PERIODIC + "\n")
        
        plumed.write("\n")

        COMBINE_LABEL = "COMBINE LABEL=classifier"
        COEFFICIENTS = "COEFFICIENTS="
        for index, row in self.classifier_features_and_weights.iterrows():
            COEFFICIENTS += str(row['weights']) + "," if index != (len(self.classifier_features_and_weights) - 1) else str(row['weights'])
        plumed.write(COMBINE_LABEL + "\n")
        plumed.write(ARG + "\n")
        plumed.write(COEFFICIENTS + " " + PERIODIC + "\n")
        plumed.write("\n")

        plumed.close()

    
    def parse_plumed_input(self, plumed_file):
        with open(plumed_file, 'r') as f:
            plumed_content = f.read()
        
        # Extract variable names and coefficients
        var_pattern = r'ARG=(.*?)\s+COEFFICIENTS=(.*?)\s+PERIODIC'
        match = re.search(var_pattern, plumed_content, re.DOTALL)
        if not match:
            raise ValueError("Could not parse PLUMED input")
        
        variables = match.group(1).split(',')
        coefficients = [float(c) for c in match.group(2).split(',')]
    
        return dict(zip(variables, coefficients))

    def combine_weights(self, weights):
        combined_weights = {}
        angle_types = set()
        specific_angles = set()
    
        # Determine which angle types are present
        for var in weights.keys():
            parts = var.split('_')
            if len(parts) >= 3 and parts[0] == 'meanfree':
                angle_type = parts[1]
                specific_angle = parts[2]
                residue = int(parts[-1])
                angle_types.add(angle_type)
                specific_angles.add(specific_angle)
                
                if residue not in combined_weights:
                    combined_weights[residue] = {}
                
                if specific_angle not in combined_weights[residue]:
                    combined_weights[residue][specific_angle] = 0
                
                combined_weights[residue][specific_angle] += weights[var] ** 2
    
        # Calculate the combined weight for each residue
        for residue in combined_weights:
            total_weight = sum(combined_weights[residue].values())
            combined_weights[residue] = math.sqrt(total_weight)
    
        return combined_weights, angle_types, specific_angles
    
    def apply_weights_to_pdb(self, pdb_file, weights, output_file):
        parser = PDB.PDBParser()
        structure = parser.get_structure("protein", pdb_file)
        
        for model in structure:
            for chain in model:
                for residue in chain:
                    res_id = residue.id[1]
                    if res_id in weights:
                        for atom in residue:
                            atom.set_bfactor(weights[res_id])
        
        io = PDB.PDBIO()
        io.set_structure(structure)
        io.save(output_file)
    
    def process_bfactor(self, plumed_file, pdb_input, pdb_output):
        weights = self.parse_plumed_input(plumed_file)
        combined_weights, angle_types, specific_angles = self.combine_weights(weights)
        self.apply_weights_to_pdb(pdb_input, combined_weights, pdb_output)
