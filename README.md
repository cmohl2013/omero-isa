# omero-isa
Transfer of OMERO metadata to ISA model

### Installation

### How to use it

* Export Omero Project
  ```bash
  omero login # login to omero
  omero transfer pack --plugin isa Project:414 path/to/my/isa-project # export
  ```

  The export produces a file structure as follows:
  ```bash
  ├── assays
  │   ├── my-first-assay
  │   │   └── dataset
  │   │       ├── 1977.tiff
  │   │       ├── 1978.tiff
  │   │       └── 1979.tiff
  │   └── my-second-assay
  │       └── dataset
  │           ├── 1980.tiff
  │           ├── 1981.tiff
  │           └── 1982.tiff
  ├── i_investigation.json
  ```


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