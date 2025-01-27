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
