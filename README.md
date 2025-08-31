# omero-isa
Transfer of OMERO metadata to ISA model

### Installation

### How to use it

* Export Omero Project
  ```bash
  omero login # login to omero
  omero transfer pack --plugin isa Project:414 path/to/my/isa-project # export
  ```


### How is OMERO data mapped to the ISA data model?

  The export of an OMERO project produces an ISA model that is represented in the follwing file structure:
  ```bash
   ├── assays
   │   ├── my-assay-with-annotations
   │   │   └── dataset
   │   │       ├── 1992.tiff
   │   │       ├── CD_s_1_t_3_c_2_z_5.czi
   |   |       |–– CD_s_1_t_3_c_2_z_5_roidata.json
   │   │       └── sted-confocal.lif
   │   └── my-first-assay
   │       └── dataset
   │           ├── 1989.tiff
   │           ├── 1990.tiff
   │           └── 1991.tiff
   ├── i_investigation.json
  ```

  * The exported OMERO project represents one ISA investigation containing exactly one study.
  * OMERO datasets are represented as ISA assays.
  * OMERO images are represented as ISA datasets. The original image files are stored within the assay folder under *dataset*.
  * If OMERO images contain ROI objects, these are exported as `json` files in the image folder. In the example above, the `czi` image includes ROI data.
  * All metadata is stored in one ISA json in the top folder.
  * If ROIs exist, the json file with ROI information is linked in the metadata `json` file as part of the image metadata.






### Install omero-isa plugin


## Development Environment Setup
```
conda create -n myenv -c conda-forge python=3.8 zeroc-ice=3.6.5
conda activate myvenv
```

### Installation
```
git clone git@github.com:cmohl2013/omero-isa.git
cd omero-isa
pip install -e .[dev] # installs optional dependencies including omero-cli-transfer
conda install pytest

```

### Start OMERO test database

Launch OMERO test environment with docker-compose.
```
sudo chmod a+x .omero/compose # enure that compose is executable
sudo .omero/compose up
```

Complete rebuild (e.g. to update omero version):
```
sudo .omero/compose up --build
```

### Run tests
```
OMERODIR="." ICE_CONFIG="test/ice.config" pytest
```

### Access to Test DB

```
http://localhost:4080/
```
Test User Credentials:

```
self.user.getOmeName()._val
```