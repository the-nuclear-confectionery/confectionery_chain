import warnings
import os
import shutil
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

        #jet sampling needs collision vertices (AMPT or TRENTo) and an active hydro.jets block
        jets_sampling = self.config['input']['hydrodynamics'].get('jets_sampling', {}) or {}
        if jets_sampling.get('enabled', False):
            vertex_source = jets_sampling.get('vertex_source', 'binary')
            ic_type = self.config['input']['initial_conditions']['type']
            ic_params = self.config['input']['initial_conditions'].get('parameters', {}) or {}
            if vertex_source == 'trento':
                # dijet vertices come from TRENTo's binary-collision list (ncoll_list0.dat)
                if ic_type != 'Trento':
                    raise ValueError(
                        "jets_sampling vertex_source 'trento' requires initial_conditions "
                        "type 'Trento'.")
                if not ic_params.get('ncoll', False):
                    raise ValueError(
                        "jets_sampling vertex_source 'trento' requires ncoll: true in the "
                        "TRENTo parameters so ncoll_list0.dat (the binary-collision vertices) "
                        "is written.")
            else:
                # 'binary' / 'minijet' vertices come from the AMPT event geometry
                if ic_type != 'ampt':
                    raise ValueError(
                        f"jets_sampling vertex_source '{vertex_source}' requires "
                        "initial_conditions type 'ampt' — the dijet vertices are sampled "
                        "from AMPT's binary-collisions.dat.")
            jets_cfg = self.config['input']['hydrodynamics'].get('hydro', {}).get('jets', {}) or {}
            if jets_cfg.get('type', 'disabled') == 'disabled':
                raise ValueError(
                    "jets_sampling is enabled but hydro.jets.type is 'disabled' — set it "
                    "to 'BBMG' (plus the BBMG parameters) so CCAKE evolves the jets.")
            sampler = os.path.join(self.config['global']['basedir'], 'utils', 'sample_dijets', 'sample_dijets')
            if not os.path.isfile(sampler):
                raise FileNotFoundError(
                    f"sample_dijets binary not found at {sampler} — build it with: ./chain rebuild sample_dijets")

        print("Base validation for CCAKE completed.")

    def prepare_jets(self, event_id):
        """Sample dijets for this event and point CCAKE's jets block at them.

        Runs utils/sample_dijets on the AMPT output of this event, converts the
        CSV to CCAKE's jets-file format, and mutates the in-memory config so
        create_temp_config() emits hydro.jets with input_mode 'file'.
        """
        from utils.jet_utils import (write_sample_dijets_config,
                                     dijets_csv_to_ccake_jets, energy_to_gev)

        jets_sampling = self.config['input']['hydrodynamics'].get('jets_sampling', {}) or {}
        if not jets_sampling.get('enabled', False):
            return

        event_dir = os.path.join(self.config['global']['output'], f"event_{event_id}")
        jets_dir = os.path.join(event_dir, 'jets')
        os.makedirs(jets_dir, exist_ok=True)
        os.makedirs(os.path.join(event_dir, 'configs'), exist_ok=True)

        sqrts_gev = energy_to_gev(self.config['global']['energy']['value'],
                                  self.config['global']['energy']['unit'])
        tau = jets_sampling.get('tau', self.config['global']['tau_hydro'])
        csv_path = os.path.join(jets_dir, 'dijets.csv')

        # binary/minijet vertices live in the AMPT output dir; trento vertices
        # (ncoll_list0.dat) live in the TRENTo output dir.
        vertex_source = jets_sampling.get('vertex_source', 'binary')
        input_dir = os.path.join(event_dir, 'trento' if vertex_source == 'trento' else 'ampt')
        conf_path = write_sample_dijets_config(
            os.path.join(event_dir, 'configs', 'sample_dijets.conf'),
            ampt_dir=input_dir,
            vertex_source=vertex_source,
            sqrts_gev=sqrts_gev,
            pt_min=jets_sampling.get('pt_min', 100.0),
            pt_max=jets_sampling.get('pt_max', 200.0),
            n_dijets=jets_sampling.get('n_dijets', 1),
            csv_file=csv_path,
            tau_hydro=tau,
        )

        sampler = os.path.join(self.config['global']['basedir'], 'utils', 'sample_dijets', 'sample_dijets')
        print(f"Sampling {jets_sampling.get('n_dijets', 1)} dijet(s) for event {event_id}")
        subprocess.run([sampler, conf_path], cwd=jets_dir, check=True)

        jets_file = os.path.join(jets_dir, 'jets.dat')
        n_jets = dijets_csv_to_ccake_jets(csv_path, jets_file)
        print(f"Wrote {n_jets} jet partons to {jets_file}")

        # Point CCAKE at the sampled jets; the file already lists both dijet
        # partons, so CCAKE must not auto-create partners.
        jets_cfg = (self.config['input']['hydrodynamics']
                    .setdefault('hydro', {})
                    .setdefault('jets', {}))
        jets_cfg['input_mode'] = 'file'
        jets_cfg['input_file'] = jets_file
        jets_cfg['auto_partner'] = False



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
        jets     = hydro.get('jets', {})
        eos      = hydrodynamics.get('eos', {})
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
                # 3D runs use the factorized SPH kernel W_2D(r_perp,h_T)*W_1D(deta,h_eta)
                'factorized_kernel': params.get('factorized_kernel', False),
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
                'normalize_by_T': eos.get('normalize_by_T', False),
                # table-EoS validity guards — BSQ (Houston) tables need
                # normalize_by_T + restrict_mu_T_ratios true to invert cleanly
                'restrict_mu_T_ratios': eos.get('restrict_mu_T_ratios', False),
                'prohibit_unstable_cs2': eos.get('prohibit_unstable_cs2', True),
                'prohibit_acausal_cs2': eos.get('prohibit_acausal_cs2', True),
                # gap-EoS (holographic / critical-point) options
                'gap_table_path': eos.get('gap_table_path', ''),
                'gap_lookup_mode': eos.get('gap_lookup_mode', 'linear'),
                'gap_analytic_enabled': eos.get('gap_analytic_enabled', False),
                'gap_match_tolerance': eos.get('gap_match_tolerance', 0.05),
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
                   'type':                source.get('type', 'disabled'),
                   'model':               source.get('model', 'disabled'),
                   'normalization':       source.get('normalization', 1.0),
                   'smearing_radius':     source.get('smearing_radius', 0.5),
                   'smearing_radius_eta': source.get('smearing_radius_eta', 0.5),
                   'file':                source.get('file', 'disabled'),
                   'enable_baryon':       source.get('enable_baryon',  False),
                   'enable_electric':     source.get('enable_electric', False),
                   'enable_strangeness':  source.get('enable_strangeness', False),
                   'propagate':           source.get('propagate', False),
                   'loss_coefficient':    source.get('loss_coefficient', 0.0),
                   'entropy_ref':         source.get('entropy_ref', 1.0),
                   'deposit_steps':       source.get('deposit_steps', 1),
                },

                'jets': {
                    'type':                  jets.get('type', 'disabled'),
                    'Energy_scaling':        jets.get('Energy_scaling', 0),
                    'Path_Length_scaling':   jets.get('Path_Length_scaling', 1),
                    'Fluctuation_parameter': jets.get('Fluctuation_parameter', 0),
                    'input_mode':            jets.get('input_mode', 'hardcoded'),
                    'input_file':            jets.get('input_file', ''),
                    'auto_partner':          jets.get('auto_partner', True),
                    'pT':                    jets.get('pT', 10.0),
                    'phi':                   jets.get('phi', 0.0),
                    'rapidity':              jets.get('rapidity', 0.0),
                    'x0':                    jets.get('x0', 0.0),
                    'y0':                    jets.get('y0', 0.0),
                    'eta0':                  jets.get('eta0', 0.0),
                    'sampling': {
                        'njet':            jets.get('sampling', {}).get('njet', 200000),
                        'sample_rapidity': jets.get('sampling', {}).get('sample_rapidity', False),
                        'rapidity_max':    jets.get('sampling', {}).get('rapidity_max', 1.0),
                    },
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
                        # CCAKE's input.cpp reads 'critical_scaling_enabled'; emit
                        # it from the same value so the flag is not silently ignored
                        # (see docs/KNOWN_ISSUES.md #3).
                        'critical_scaling_enabled': bulk.get('critical_scaling_bulk', False),
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
                        'critical_point':          diff.get('critical_point', {'T': 150.0, 'muB': 350.0}),
                        'critical_gaussian_width': diff.get('critical_gaussian_width', {'T': 25.0, 'muB': 100.0}),
                        'regulator': {
                            'enabled': diff.get('regulator', {}).get('enabled', False),
                            'chi0':    diff.get('regulator', {}).get('chi0', 10.0),
                            'e0':      diff.get('regulator', {}).get('e0', 0.1),
                            'xi0':     diff.get('regulator', {}).get('xi0', 0.01),
                            'rq_max':  diff.get('regulator', {}).get('rq_max', 1.0),
                        },
                    },
                },
            },
            'output': {
                'print_conservation_state': output['print_conservation_state'],
                'hdf_evolution': output['hdf_evolution'],
                'txt_evolution': output['txt_evolution'],
                'evolution_stride': output.get('evolution_stride', 1),
                'jet_evolution': output.get('jet_evolution', False),
                'get_neighbors': output.get('get_neighbors', False),
                'calculate_observables': output.get('calculate_observables', False),
                'check_causality': output.get('check_causality', True),
                'causality_minimal': output.get('causality_minimal', False),
                'causality_minimal_stride': output.get('causality_minimal_stride', 20),
            }
        }

        # Write the configuration to the temporary file
        with open(temp_config_path, 'w') as f:
            yaml.dump(temp_config, f, default_flow_style=False)

        print(f"Temporary configuration created at: {temp_config_path}")


    def run(self, event_id):
        #sample jets first (no-op unless jets_sampling.enabled)
        self.prepare_jets(event_id)
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

        # persist the freeze-out surface to the top-level output dir so it
        # survives end-of-run cleanup. Controlled by the per-stage
        # 'keep_result' flag.
        keep_result = self.config['input']['hydrodynamics'].get('parameters', {}).get('keep_result', False)
        if keep_result:
            freeze_out_src = os.path.join(output_dir, "freeze_out.dat")
            if os.path.exists(freeze_out_src):
                dest = os.path.join(self.config['global']['output'], f"freeze_out_{event_id}.dat")
                shutil.copy2(freeze_out_src, dest)
                print(f"Persisted freeze-out surface to {dest}")

        #insert into db
        insert_hydro(self.db_connection,
                     event_id=event_id,
                     initial_time=self.config['global']['tau_hydro'],
                     freeze_out_temperature=self.config['input']['hydrodynamics']['particlization']['T'],
                     dimensions= self.config['input']['hydrodynamics']['initial_conditions']['dimension'],
                     hydro_type=self.config['input']['hydrodynamics']['type'],
                     )
     
