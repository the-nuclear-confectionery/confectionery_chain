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
                'dt': hydrodynamics['parameters']['dt'],
                'h_T': hydrodynamics['parameters']['h_T'],
                'h_eta': hydrodynamics['parameters']['h_eta'],
                'rk_order': hydrodynamics['parameters']['rk_order'],
                'kernel_type': hydrodynamics['parameters']['kernel_type'],
                'energy_cutoff': hydrodynamics['parameters']['energy_cutoff'],
                'max_tau': hydrodynamics['parameters']['max_tau'],
                'buffer_particles': {
                    'enabled': hydrodynamics['parameters']['buffer_particles']['enabled'],
                    'circular': hydrodynamics['parameters']['buffer_particles']['circular'],
                    'padding_thickness': hydrodynamics['parameters']['buffer_particles']['padding_thickness']
                }
            },
            'eos': {
                'type': hydrodynamics['eos']['type'],
                'path': hydrodynamics['eos']['path'],
                'online_inverter_enabled': hydrodynamics['eos']['online_inverter_enabled'],
                'preinverted_eos_path': hydrodynamics['eos']['preinverted_eos_path']
            },
            'particlization': {
                'enabled': hydrodynamics['particlization']['enabled'],
                'type': hydrodynamics['particlization']['type'],
                'T': hydrodynamics['particlization']['T']
            },
            'hydro': {
                                                                                                                                                                                                                                'baryon_charge_enabled':  hydrodynamics['hydro']['baryon_charge_enabled'],
                'strange_charge_enabled': hydrodynamics['hydro']['strange_charge_enabled'],
                'electric_charge_enabled': hydrodynamics['hydro']['electric_charge_enabled'],
            
                'viscous_parameters': {
                    'shear': {
                        'input_initial_shear':  hydrodynamics['hydro']['viscous_parameters']['shear']['input_initial_shear'],
                        'mode':                 hydrodynamics['hydro']['viscous_parameters']['shear']['mode'],
                        'constant_eta_over_s':  hydrodynamics['hydro']['viscous_parameters']['shear']['constant_eta_over_s'],
                        'relaxation_mode':      hydrodynamics['hydro']['viscous_parameters']['shear']['relaxation_mode'],
                        'use_vorticity':        hydrodynamics['hydro']['viscous_parameters']['shear']['use_vorticity'],
                        'delta_pipi_mode':      hydrodynamics['hydro']['viscous_parameters']['shear']['delta_pipi_mode'],
                        'tau_pipi_mode':        hydrodynamics['hydro']['viscous_parameters']['shear']['tau_pipi_mode'],
                        'lambda_piPi_mode':     hydrodynamics['hydro']['viscous_parameters']['shear']['lambda_piPi_mode'],
                        'phi6_mode':            hydrodynamics['hydro']['viscous_parameters']['shear']['phi6_mode'],                                                                 
                        'phi7_mode':            hydrodynamics['hydro']['viscous_parameters']['shear']['phi7_mode'],
                    },
            
                    'bulk': {
                        'bulk_from_trace':      hydrodynamics['hydro']['viscous_parameters']['bulk']['bulk_from_trace'],
                        'mode':                 hydrodynamics['hydro']['viscous_parameters']['bulk']['mode'],
                        'constant_zeta_over_s': hydrodynamics['hydro']['viscous_parameters']['bulk']['constant_zeta_over_s'],
                        'cs2_dependent_zeta_A': hydrodynamics['hydro']['viscous_parameters']['bulk']['cs2_dependent_zeta_A'],
                        'cs2_dependent_zeta_p': hydrodynamics['hydro']['viscous_parameters']['bulk']['cs2_dependent_zeta_p'],
                        'relaxation_mode':      hydrodynamics['hydro']['viscous_parameters']['bulk']['relaxation_mode'],
                        'modulate_with_tanh':   hydrodynamics['hydro']['viscous_parameters']['bulk']['modulate_with_tanh'],
                        'delta_PiPi_mode':      hydrodynamics['hydro']['viscous_parameters']['bulk']['delta_PiPi_mode'],
                        'lambda_Pipi_mode':     hydrodynamics['hydro']['viscous_parameters']['bulk']['lambda_Pipi_mode'],
                        'phi1_mode':            hydrodynamics['hydro']['viscous_parameters']['bulk']['phi1_mode'],
                        'phi3_mode':            hydrodynamics['hydro']['viscous_parameters']['bulk']['phi3_mode'],
                    },
            
                    'diffusion': {
                        'input_initial_diffusion': hydrodynamics['hydro']['viscous_parameters']['diffusion']['input_initial_diffusion'],
                        'mode':                    hydrodynamics['hydro']['viscous_parameters']['diffusion']['mode'],
                        'constant_kappa_over_T2':  hydrodynamics['hydro']['viscous_parameters']['diffusion']['constant_kappa_over_T2'],
                        'relaxation_mode':         hydrodynamics['hydro']['viscous_parameters']['diffusion']['relaxation_mode'],
                    },
                },
            },
            'output': {
                'print_conservation_state': hydrodynamics['output']['print_conservation_state'],
                'hdf_evolution': hydrodynamics['output']['hdf_evolution'],
                'txt_evolution': hydrodynamics['output']['txt_evolution'],
                'calculate_observables': hydrodynamics['output']['calculate_observables'],
                'check_causality': hydrodynamics['output']['check_causality'],
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
     