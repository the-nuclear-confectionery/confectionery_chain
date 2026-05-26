import warnings
import os
import subprocess
import re
import pandas as pd
import random
from stages.hydrodynamics import Hydrodynamics
from utils.db import insert_hydro
import yaml

class CCAKEHydro(Hydrodynamics):

    def validate(self, event_id):
        """Perform validation specific to CCAKE if it's enabled."""
        
        if self.config['input']['hydrodynamics']['type'] != 'CCAKE':
            return  # Skip validation if CCAKE is not the active hydro
        grid = self.config['global']['grid']
        print("Base validation for CCAKE started.")
        if grid['step_eta'] > 0:
            print("Step_eta is non-zero, initializing 3D hydro.")
            self.config['input']['hydrodynamics']['initial_conditions']['dimension'] = 3
        else:
            print("Step_eta is zero, initializing 2D hydro.")
            self.config['input']['hydrodynamics']['initial_conditions']['dimension'] = 2

        #check the initial condition path
        if self.config['input']['hydrodynamics']['initial_conditions']['file'] == 'default':
            #check the initial condition type
            if self.config['input']['initial_conditions']['type'] == 'Trento':
                #check for iccing overlay
                if self.config['input']['overlay']['type'] == 'ICCING':
                    #file is the ICCING output 
                    self.config['input']['hydrodynamics']['initial_conditions']['file'] = \
                        os.path.join(self.config['global']['output'], f"event_{event_id}", 'iccing', 'densities0.dat')
                    #set IC type in CCAKE to 'ICCING'
                    self.config['input']['hydrodynamics']['initial_conditions']['type'] = 'ICCING'
                elif self.config['input']['preequilibrium']['type'] == 'freestreaming':
                    #check if file is set
                    print("Reading freestreaming file")
                    self.config['input']['hydrodynamics']['initial_conditions']['file'] = \
                        os.path.join(self.config['global']['output'], f"event_{event_id}", 'freestream', 'fs.dat')

                    self.config['input']['hydrodynamics']['initial_conditions']['type'] = 'ccake'
                else:
                    #file is the default output of trento
                    self.config['input']['hydrodynamics']['initial_conditions']['file'] = \
                        os.path.join(self.config['global']['output'], f"event_{event_id}", 'trento', 'ccake_ic.dat')
                    #set IC type in CCAKE to 'Trento'
                    self.config['input']['hydrodynamics']['initial_conditions']['type'] = 'ccake'
                    #set read as entropy
                    #self.config['input']['hydrodynamics']['initial_conditions']['input_as_entropy'] = True
            

            #check for AMPT overlay
            if self.config['input']['overlay']['type'] == 'AMPTGenesis':
                #file is the AMPT output
                self.config['input']['hydrodynamics']['initial_conditions']['file'] = \
                    os.path.join(self.config['global']['output'], f"event_{event_id}", 'amptgenesis', 'ccake_ic.dat')
                #set IC type in CCAKE to 'AMPT'
                self.config['input']['hydrodynamics']['initial_conditions']['type'] = 'ccake'
            
            #check for none initial conditions or overlay or preequilibrium
            if self.config['input']['initial_conditions']['type'] == None and self.config['input']['overlay']['type'] == None and self.config['input']['preequilibrium']['type'] == None:
                #error 
                raise ValueError("No initial conditions or overlay specified, so initial condition file amd IC type must be specified.")  
            #check for freestreaming preequilibrium
        else:
            #check if ic type is set. It should always be set if the file is not default
            if self.config['input']['hydrodynamics']['initial_conditions']['type'] == 'default':
                #error 
                raise ValueError("Initial condition type value in CCAKE yaml must be specified when reading from external file.")
            

        #check eos path
        if self.config['input']['hydrodynamics']['eos']['path'] == 'default':
            self.config['input']['hydrodynamics']['eos']['path'] = os.path.join(self.config['global']['basedir'], 'tables')

        print("Base validation for CCAKE completed.")



    def create_temp_config(self, event_id):
        """Create a temporary CCAKE configuration file using the YAML-provided parameters."""
        if self.config['input']['hydrodynamics']['type'] != 'CCAKE':
            raise ValueError("create_temp_config should only be called when CCAKE is the active hydro.")

        # Build output paths
        output_dir = os.path.join(self.config['global']['output'], f"event_{event_id}", 'ccake')
        os.makedirs(output_dir, exist_ok=True)

        config_dir = os.path.join(self.config['global']['output'], f"event_{event_id}", 'configs')
        os.makedirs(config_dir, exist_ok=True)

        # Path for the temporary configuration file
        temp_config_path = os.path.join(config_dir, f"ccake.yaml")

        # Get hydrodynamics section from the main configuration
        hydrodynamics = self.config['input']['hydrodynamics']

        # Helpers for nested .get() access
        params   = hydrodynamics.get('parameters', {})
        hydro    = hydrodynamics.get('hydro', {})
        visc     = hydro.get('viscous_parameters', {})
        shear    = visc.get('shear', {})
        bulk     = visc.get('bulk', {})
        diff     = visc.get('diffusion', {})
        source   = hydro.get('source', {})
        output   = hydrodynamics.get('output', {})

        # Construct the configuration by cropping relevant sections
        temp_config = {
            'initial_conditions': {
                'type': hydrodynamics['initial_conditions']['type'],
                'file': hydrodynamics['initial_conditions']['file'],
                'dimension': hydrodynamics['initial_conditions']['dimension'],
                'input_as_entropy': hydrodynamics['initial_conditions']['input_as_entropy'],
                't0': self.config['global']['tau_hydro'],
                'coordinate_system': hydrodynamics['initial_conditions']['coordinate_system']
            },
            'parameters': {
                'dt': params['dt'],
                'h_T': params['h_T'],
                'h_eta': params['h_eta'],
                'rk_order': params.get('rk_order', 2),
                'kernel_type': params['kernel_type'],
                'energy_cutoff': params['energy_cutoff'],
                'max_tau': params.get('max_tau', 30.0),
                'buffer_particles': {
                    'enabled': params['buffer_particles']['enabled'],
                    'circular': params['buffer_particles']['circular'],
                    'padding_thickness': params['buffer_particles']['padding_thickness']
                }
            },
            'eos': {
                'type': hydrodynamics['eos']['type'],
                'path': hydrodynamics['eos']['path'],
                'online_inverter_enabled': hydrodynamics['eos']['online_inverter_enabled'],
                'preinverted_eos_path': hydrodynamics['eos'].get('preinverted_eos_path', 'default'),
                'normalize_by_T': hydrodynamics['eos'].get('normalize_by_T', False),
            },
            'particlization': {
                'enabled': hydrodynamics['particlization']['enabled'],
                'type': hydrodynamics['particlization']['type'],
                'T': hydrodynamics['particlization']['T']
            },
            'hydro': {
                'baryon_charge_enabled': hydro['baryon_charge_enabled'],
                'strange_charge_enabled': hydro['strange_charge_enabled'],
                'electric_charge_enabled': hydro['electric_charge_enabled'],
                'source': {
                   'type':            source.get('type', 'disabled'),
                   'model':           source.get('model', 'disabled'),
                   'normalization':   source.get('normalization', 1.0),
                   'smearing_radius': source.get('smearing_radius', 1.4),
                   'file':            source.get('file', 'disabled'),
                   'enable_baryon':   source.get('enable_baryon',  False),
                   'enable_electric': source.get('enable_electric', False),
                   'enable_strange':  source.get('enable_strange', False),
                },

                'viscous_parameters': {
                    'shear': {
                        'input_initial_shear':  shear.get('input_initial_shear', False),
                        'mode':                 shear['mode'],
                        'constant_eta_over_s':  shear['constant_eta_over_s'],
                        'relaxation_mode':      shear['relaxation_mode'],
                        'use_vorticity':        shear.get('use_vorticity', False),
                        'delta_pipi_mode':      shear.get('delta_pipi_mode', 'default'),
                        'tau_pipi_mode':        shear.get('tau_pipi_mode', 'disabled'),
                        'lambda_piPi_mode':     shear.get('lambda_piPi_mode', 'disabled'),
                        'phi6_mode':            shear.get('phi6_mode', 'disabled'),
                        'phi7_mode':            shear.get('phi7_mode', 'disabled'),
                    },

                    'bulk': {
                        'bulk_from_trace':        bulk.get('bulk_from_trace', False),
                        'mode':                   bulk['mode'],
                        'constant_zeta_over_s':   bulk['constant_zeta_over_s'],
                        'cs2_dependent_zeta_A':   bulk['cs2_dependent_zeta_A'],
                        'cs2_dependent_zeta_p':   bulk['cs2_dependent_zeta_p'],
                        'relaxation_mode':        bulk['relaxation_mode'],
                        'modulate_with_tanh':     bulk['modulate_with_tanh'],
                        'critical_scaling_bulk':  bulk.get('critical_scaling_bulk', False),
                        'delta_PiPi_mode':        bulk.get('delta_PiPi_mode', 'israel-stewart'),
                        'lambda_Pipi_mode':       bulk.get('lambda_Pipi_mode', 'default'),
                        'phi1_mode':              bulk.get('phi1_mode', 'disabled'),
                        'phi3_mode':              bulk.get('phi3_mode', 'disabled'),
                    },

                    'diffusion': {
                        'input_initial_diffusion': diff.get('input_initial_diffusion', False),
                        'mode':                    diff.get('mode', 'constant_over_T2'),
                        'constant_kappa_over_T2':  diff.get('constant_kappa_over_T2', [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]),
                        'relaxation_mode':         diff.get('relaxation_mode', 'constant_over_T'),
                        'critical_scaling':        diff.get('critical_scaling', False),
                        'critical_point':          diff.get('critical_point', {'T': 0.0, 'muB': 0.0}),
                        'critical_gaussian_width': diff.get('critical_gaussian_width', {'T': 25.0, 'muB': 100.0}),
                    },
                },
            },
            'output': {
                'print_conservation_state': output['print_conservation_state'],
                'hdf_evolution': output['hdf_evolution'],
                'txt_evolution': output['txt_evolution'],
                'calculate_observables': output.get('calculate_observables', False),
                'check_causality': output.get('check_causality', True),
            }
        }

        # Write the configuration to the temporary file
        with open(temp_config_path, 'w') as f:
            yaml.dump(temp_config, f, default_flow_style=False)

        print(f"Temporary configuration created at: {temp_config_path}")


    def run(self, event_id):
        #create temp config
        self.create_temp_config(event_id)
        ccake_executable = self.config['global']['basedir'] + '/models/CCAKE/build/ccake'
        #run ccake
        output_dir = os.path.join(self.config['global']['output'], f"event_{event_id}", 'ccake')
        print("Running CCAKE")
        command = f"{ccake_executable} {os.path.join(self.config['global']['output'], f'event_{event_id}', 'configs', 'ccake.yaml')} {output_dir}"
        #os.system(command)
        subprocess.run([ccake_executable, 
                os.path.join(self.config['global']['output'], f'event_{event_id}', 'configs', 'ccake.yaml'), 
                output_dir], check=True)

        #insert into db
        insert_hydro(self.db_connection, 
                     event_id=event_id, 
                     initial_time=self.config['global']['tau_hydro'],
                     freeze_out_temperature=self.config['input']['hydrodynamics']['particlization']['T'],
                     dimensions= self.config['input']['hydrodynamics']['initial_conditions']['dimension'],
                     hydro_type=self.config['input']['hydrodynamics']['type'],
                     )
     