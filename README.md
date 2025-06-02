# Policy Derived Data Access Management Platform for a Network of Heterogenous Storage Endpoints

Developed for use by:
1. [The Institute for Neuroscience and Neurotechnology](https://www.sfu.ca/neuro-institute.html)
2. [Research Computing Group](https://www.rcg.sfu.ca/)

* Principal Architect and Development: [pmahon@sfu.ca](mailto:pmahon@sfu.ca) <sup>1,2</sup>
* Consultation: [jpeltier@sfu.ca](mailto:jpeltier@sfu.ca) <sup>2</sup>
* Consultation: [kshen@sfu.ca](mailto:kshen@sfu.ca) <sup>1</sup>

For detailed info please wee the [wiki](https://github.com/INN-SFU/Data-Portal/wiki).

# Setup 

1. Clone the repo.
2. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Ask [pmahon@sfu.ca](mailto:pmahon@sfu.ca) for the `config.yaml`
4. Set up `keycloak` service
   - Get the `keycloak` image from [pmahon3@sfu.ca]
   - Start the service with `???`
5. Run 'Data-Portal /main.py` to start the application.
