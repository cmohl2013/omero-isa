# omero-isa
Transfer of OMERO metadata to ISA model

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