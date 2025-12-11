from stages.analysis import Analysis
import os
import subprocess
import yaml
from utils.db import insert_analysis


class QVectorWritterAnalysis(Analysis):

    def __init__(self, config, db_connection):
        self.config = config
        self.db_connection = db_connection

    def validate(self, event_id):
        parameters = self.config['input']['analysis']['parameters']

        # Check for afterburner
        if self.config['input']['afterburner']['type'] is None:
            if self.config['input']['particlization']['type'] == 'analytical':
                parameters['input_file'] = os.path.join(
                    self.config['global']['output'],
                    f"event_{event_id}",
                    "analytical",
                    "corrected_spectra.dat"
                )
                if 'input_type' not in parameters or parameters['input_type'] == 'default':
                    parameters['input_type'] = 'afterdecays'
                print("No afterburner specified; using corrected spectra from analytical cooperfrye")
            else:
                if parameters.get('input_file', 'default') == 'default':
                    raise ValueError("Afterburner is disabled, input_file must be specified.")
                if parameters.get('input_type' ) == 'default':
                    raise ValueError("Afterburner is disabled, input_type must be specified.")
        elif self.config['input']['afterburner']['type'] == 'smash':
            formats = self.config['input']['afterburner']['parameters']['Output']['Particles']['Format']
            output_path = os.path.join(
                self.config['global']['output'],
                f"event_{event_id}",
                "smash"
            )
            # --- Determine default input file and type ---
            if 'HepMC_treeroot' in formats:
                parameters['input_file'] = os.path.join(output_path, "SMASH_HepMC_particles.root")
                if 'input_type' not in parameters or parameters['input_type'] == 'default':
                    parameters['input_type'] = 'smash_hepmc3'
            elif 'Oscar2013' in formats:
                parameters['input_file'] = os.path.join(output_path, "particles.oscar")
                if 'input_type' not in parameters or parameters['input_type'] == 'default':
                    parameters['input_type'] = 'smash_oscar'
            else:
                print("Using SMASH default format")
                parameters['input_file'] = os.path.join(output_path, "SMASH_HepMC_particles.root")
                if 'input_type' not in parameters or parameters['input_type'] == 'default':
                    parameters['input_type'] = 'smash_hepmc3'
        elif self.config['input']['afterburner']['type'] == 'afterdecays':
            print("afterdecays afterburner detected, using its output.")
            parameters['input_file'] = os.path.join( self.config['global']['output'],
                f"event_{event_id}",
                "afterdecays",
                "output.dat"
            )
            if 'input_type' not in parameters or parameters['input_type'] == 'default':
                parameters['input_type'] = 'afterdecays'


        # Resolve output file
        if parameters.get('output_file', 'default') == 'default':
            parameters['output_file'] = os.path.join(
                self.config['global']['output'],
                f"q_{event_id}"
            )

        print(f"qvector writter validation done")
        print(f"input_file:  {parameters['input_file']}")
        print(f"output_file: {parameters['output_file']}")
        print(f"input_type:  {parameters['input_type']}")


    def create_temp_config(self, event_id):
        parameters = self.config['input']['analysis']['parameters']

        # Destination path
        config_dir = os.path.join(self.config['global']['output'], f"event_{event_id}", "configs")
        os.makedirs(config_dir, exist_ok=True)
        temp_config_path = os.path.join(config_dir, "qvector_config.yaml")

        # Extract relevant config keys
        qvector_config = {
            'n_max': parameters.get('n_max'),
            'calculate_charged': parameters.get('calculate_charged'),
            'pids': parameters.get('pids'),
            'pt_bins': parameters.get('pt_bins'),
            'max_pt': parameters.get('max_pt'),
            'eta_bins': parameters.get('eta_bins'),
            'max_eta': parameters.get('max_eta'),
            'input_type': parameters.get('input_type'),
            'output_type': parameters.get('output_type'),
        }

        if 'pt_bins_custom' in parameters:
            qvector_config['pt_bins_custom'] = parameters['pt_bins_custom']
        if 'eta_bins_custom' in parameters:
            qvector_config['eta_bins_custom'] = parameters['eta_bins_custom']

        # Write YAML
        with open(temp_config_path, 'w') as f:
            yaml.dump(qvector_config, f, default_flow_style=False)

        print(f"Written config to {temp_config_path}")
        return temp_config_path

    def run(self, event_id):
        parameters = self.config['input']['analysis']['parameters']
        input_file = parameters['input_file']
        output_file = parameters['output_file']

        # Generate YAML config file
        config_path = self.create_temp_config(event_id)

        # Path to executable
        exe = os.path.join(self.config['global']['basedir'], "models/qvector_writter/build/qvector_writter.exe")

        # Execute
        cmd = [exe, input_file, output_file, config_path]
        print(f"Running qvector_writter:\n  {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

        # Save to DB
        insert_analysis(
            self.db_connection,
            event_id=event_id,
            n_max=parameters['n_max'],
            analysis_type='qvector_writter'
        )
