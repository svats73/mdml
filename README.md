# MDML: Deep Learning for Molecular Simulation

**Framework**

![fig1](/image-mdml.png)

MDML enables training ML model on molecular dynamics simulation data to capture structural features that governs slowly varying conformational motions. The output of `mdml` can be integrated with enhanced sampling and Markov State model. 

## Overview

MDML is a powerful command-line interface (CLI) tool designed for the analysis of molecular dynamics (MD) simulations. Leveraging the capabilities of`mdml` library, MDML facilitates the loading of MD trajectory data, the featurization of trajectories, the execution of Slow Feature Analysis (SFA) and Variational Autoencoding, and the creation of PLUMED files for biasing simulations based on SFA and VAE components. 

## 🌟 Highlights

1. **Dihedral Featurization of MD Dataset**
   Extract backbone and sidechain torsion angles to represent conformational states.

2. **Slow Feature Analysis (SFA) on Dihedral Features**
   Identify the slowest collective motions driving conformational transitions.

3. **Clustering on SFA Space**
   Clustering on the SFA space for downstream kinetic modeling and adaptive sampling.

4. **Time-lagged Auto-Encoder (ML) on Dihedral Features**
   A deep learning framework to capture non-linear reaction coordinates.

5. **Generation of PLUMED Files for Enhanced Sampling**
   Auto-generate biasing scripts for enhanced sampling.

6. **Utility Scripts to Map ML Weights to PDB to Capture Hotspots**
   Project feature importance onto 3D structure for hotspot identification.

7. **Classifier to Distinguish Conformational Ensembles**
   Train binary models to classify simulation ensembles and capture hotspots.

## Custom Installation

Before installing MDML, it is necessary to install a custom version of `sklearnsfa`, which is packaged within the `mdml` repository, as well as msmbuilder2022 found at https://github.com/msmbuilder/msmbuilder2022. This ensures compatibility and optimal performance for SFA computations within MDML. Follow these steps to install both the custom `sklearnsfa` and `mdml`:

1. **Install msmbuilder2022 using conda:**
``` conda install -c conda-forge testmsm ```

Alternatively, one can install msmbuilder2022 with pip by cloning the repository at https://github.com/msmbuilder/msmbuilder2022 and running:

``` pip install ./msmbuilder2022 ```

2. **Clone the `mdml` repository to your local machine:**
``` git clone https://github.com/svats73/mdml.git ```

3. **Navigate to the cloned repository directory:**
``` cd mdml ```

4. **Install the custom `sklearnsfa` package:**
``` pip install ./sklearn-sfa ```

5. **Install the `mdml` package:**
``` pip install . ```

This installation process will ensure that you have both the `mdml` tool and the custom `sklearn-sfa` library installed and ready for your MD analysis tasks.

## Usage

The MDML CLI tool supports various commands for processing and analyzing your MD trajectories. Below is a guide to using these commands:

### Loading Trajectories

``` mdml load-trajectories --path_to_trajectories PATH --topology_file FILE --stride N --atom_indices "selection" ```

- `--path_to_trajectories`: Directory containing trajectory files.
- `--topology_file`: Topology file path.
- `--stride`: Interval for loading frames (optional).
- `--atom_indices`: Atom selection string (optional).

### Featurizing Dihedrals

``` mdml featurize --types TYPE1 --types TYPE2 --nosincos ```

- `--types`: Types of dihedrals to featurize. Can specify multiple types, such as chi1, chi2, phi, psi. `--types` must be put before each type input
- `--nosincos`: Disables the sin/cos transformation if set.

### Describing Features

``` mdml describe-features --nosincos ```

- `--nosincos`: Disables the sin/cos transformation if set.

### Dumping Description

``` mdml dump-description --description_file_path PATH --nosincos ```

- `--description_file_path`: File path to save the feature description.
- `--nosincos`: Dump non-transformed feature description if created.

### Dumping Featurized Data

``` mdml dump-featurized --dump_file_path PATH --nosincos ```

- `--dump_file_path`: File path to save the featurized data.
- `--nosincos`: Dump non-transformed features if created.

### Running Slow Feature Analysis (SFA)

``` mdml run-sfa --n_components N --tau T ```

- `--n_components`: Number of SFA components to extract.
- `--tau`: The lag time for SFA.

### Creating PLUMED File

``` mdml create-plumed_file --plumed_filename FILENAME ```

- `--plumed_filename`: File path to save the generated PLUMED file.

### Dumping SFA Components

``` mdml dump-sfa-components --save_file FILE ```

- `--save_file`: File path to save the SFA components. This will create a .pkl file which you can use to build Markov State Model.

### Cluster on SFA Components

``` mdml cluster --algorithm ALGORITHM_NAME --n_clusters NUMBER_OF_CLUSTERS ```

- `--algorithm`: Name of clustering algorithm to use (currently supporting 'kcenters', 'kmeans', and 'gmm')
- `--n_clusters`: For 'kcenters' and 'kmeans', how many cluster centers to use (optional, unused for 'gmm')

### Dumping structures clustered on SFA Components

``` mdml dump-clusters --num_samples NUMBER_OF_SAMPLES ```

- `--num_samples`: Number of structures to sample from cluster centers generated by clustering to be dumped

### Classify ensembles

``` mdml classify --ensemble_one PATH_TO_FIRST_ENSEMBLES --ensemble_two PATH_TO_SECOND_ENSEMBLES --ensemble_features ```

- `--ensemble_one`: Path to first featurized ensemble of trajectories
- `--ensemble_two`: Path to second featurized ensemble of trajectories
- `--ensemble_features`: Path to dataframe which contains featurization information for the given ensembles

### Dump classified ensembles as a plumed file

``` mdml create-classifier-plumed --plumed_filename FILENAME ```

- `--plumed_filename`: File path to save the generated PLUMED file.

### Train VAE 
 
 ``` md-sfa train-vae --pickle_descriptor PICKLE_DESCRIPTOR_FILE --pickle_features PICKLE_FEATURES_FILE --pickle_features --tau TAU_VALUE ```
 
 - `--pickle_descriptor`: One or more file paths to pickles used as descriptors for the system
 - `--pickle_features`: One or more file paths to pickles used as features for the system
 - `--tau`: Time lag parameter (integer)

**This will generate a `plumed` file which can be used for enhanced sampling. The output `cv_pred.npz` can be used to build Markov State Model.**
 
 NOTE: you can add multiple pickle descriptors/features by adding additional `--pickle_descriptor` flags before additional paths to descriptors/features, ensure that the ordering is the same for descriptors and features 
 
 ### Predict VAE 
 
 ``` md-sfa train-vae --pickle_descriptor PICKLE_DESCRIPTOR_FILE --pickle_features PICKLE_FEATURES_FILE --pickle_features --tau TAU_VALUE --model_path PATH_TO_TRAINED_MODEL --teacher_flag (OPTIONAL)```
 
 - `--pickle_descriptor`: One or more file paths to pickles used as descriptors for the system
 - `--pickle_features`: One or more file paths to pickles used as features for the system
 - `--tau`: Time lag parameter (integer)
 - `--model_path`: Path to model trained on given descriptors and features
 - `--teacher_flag` : Optional flag to make predictions with teacher mode
 
 NOTE: you can add multiple pickle descriptors/features by adding additional `--pickle_descriptor` flags before additional paths to descriptors/features, ensure that the ordering is the same for descriptors and features 


### Dumping SFA Weights as B-Factors

``` mdml plumed-bfactor --dat_file FILE --pdb_input PDB_INPUT_FILE --pdb_output PDB_OUTPUT_FILE ```

- `--dat_file`: File path containing saved SFA components.
- `--pdb_input`: File path to PDB on which SFA weights will be dumped.
- `--pdb_input`: Output filename for PDB with added SFA weights.

![ga](/sfa-weights.png)

### Restarting the Tool

To clear the current state and start fresh:

``` mdml restart ```

This command deletes any serialized state, allowing you to start a new analysis without interference from previous runs.

## 🔮 Future Improvements

1. **ML and SFA on Distances**
   Extend featurization to inter-residue distances .

2. **Clustering on ML Space**
   Cluster in latent space to discover novel states.

3. **Generation of PLUMED Files with ML/SFA on Distances**
   Bias distances-based coordinates in enhanced sampling.

4. **Utility Scripts to Map ML/SFA (Distances) Weights to PDB**
   Visualize distance-derived importance on structures.

5. **Combine Dihedral and Distances in a 2D ML Space**
   Integrate multiple feature types for richer reaction coordinates.

## Team 

Contributors: Shray Vats, Andreas Mardt, Soumendranath Bhakat

Contact: Shray Vats, email: `<firstname><lastname>@gmail.com`

## References 

If you use `mdml` for your research, make sure to cite the following:
1. Generalizable Protein Dynamics in Serine-Threonine Kinases: Physics is the key Soumendranath Bhakat, Shray Vats, Andreas Mardt, Alexei Degterev bioRxiv 2025.03.06.641878; doi: https://doi.org/10.1101/2025.03.06.641878
2. Vats S, Bobrovs R, Söderhjelm P, Bhakat S (2024) AlphaFold-SFA: Accelerated sampling of cryptic pocket opening, protein-ligand binding and allostery by AlphaFold, slow feature analysis and metadynamics. PLOS ONE 19(8): e0307226. https://doi.org/10.1371/journal.pone.0307226
3. Mardt, A., Pasquali, L., Wu, H. et al. VAMPnets for deep learning of molecular kinetics. Nat Commun 9, 5 (2018). https://doi.org/10.1038/s41467-017-02388-1

