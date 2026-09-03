from utils.input_file import InputFile
from specializations.trento_initial_condition import TrentoInitialCondition
from specializations.ICCING_overlay import ICCINGOverlay
from specializations.freestreaming_preequilibrium import Freestreaming
from specializations.ccake_hydro import CCAKEHydro
from specializations.is3d_particlization import iS3DParticlization
from specializations.BQSSampler_particlization import BQSSamplerParticlization
from specializations.analytical_particlization import AnalyticalParticlization
from specializations.smash_afterburner import SMASHAfterburner
from specializations.afterdecays_afterburner import AfterdecaysAfterburner
from specializations.qvector_writter_analysis import QVectorWritterAnalysis
from specializations.ampt_initial_condition import AmptInitialCondition
from specializations.amptgenesis_overlay import AmptGenesisOverlay
from specializations.none_hydro import NoneHydro
from specializations.none_initial_condition import NoneInitialCondition
from specializations.none_overlay import NoneOverlay
from specializations.none_preequilibrium import NonePreequilibrium
from specializations.none_particlization import NoneParticlization
from specializations.none_afterburner import NoneAfterburner
from specializations.none_analysis import NoneAnalysis
from utils.validate_collision_system import CollisionSystem
from utils.db import initialize_database, insert_event, update_event_centrality_estimator, update_ic_type, update_overlay_type\
                    , update_hydro_type, update_particlization_type, update_afterburner_type, update_analysis_type, update_preequilibrium_type
import argparse
import os
import shutil

def main():
    centrality_estimator = None

    parser = argparse.ArgumentParser(description="Run initial condition generation and overlay for a specific event.")
    parser.add_argument('event_id', type=int, help="Event ID to run.")
    parser.add_argument('db_path', type=str, help="Path to the SQLite database.")
    parser.add_argument('config_path', type=str, help="Path to the configuration file.")
    args = parser.parse_args()

    # Initialize database connection
    db_connection = initialize_database(args.db_path)
    #config = InputFile("input.yml").get_parameters()
    config = InputFile(args.config_path).get_parameters()

    # --- auto-fill machine paths so a scenario runs with no hand-editing ---
    # basedir defaults to this repo (the parent of wrapper/); output/tmp default under it.
    # Set any of these to a real path in the yaml to override.
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    g = config['global']
    if str(g.get('basedir', 'default')).lower() in ('default', 'none', ''):
        g['basedir'] = repo_root
    if str(g.get('output', 'default')).lower() in ('default', 'none', ''):
        g['output'] = os.path.join(g['basedir'], 'sample_output')
    if str(g.get('tmp', 'default')).lower() in ('default', 'none', ''):
        g['tmp'] = os.path.join(g['basedir'], 'sample_tmp')

    # Create results and tmp directories for event id
    os.makedirs(os.path.join(config['global']['output'], f"event_{args.event_id}"), exist_ok=True)
    os.makedirs(os.path.join(config['global']['tmp'], f"event_{args.event_id}"), exist_ok=True)
    tables_dir = os.path.join(config['global']['basedir'], "tables")
    #copy tables dir to tmp dir with rsync
    os.system(f"rsync -a {tables_dir} {os.path.join(config['global']['tmp'], f'event_{args.event_id}')}/") 
    
    #copy config to output dir
    shutil.copy(args.config_path, os.path.join(config['global']['output'], f"event_{args.event_id}", "config.yml"))

    collision_system = CollisionSystem(config, db_connection)
    collision_id = collision_system.insert_collision_system()
    # Insert event (without centrality_estimator yet)
    insert_event(
        db_connection,
        args.event_id,
        config['global']['output']+"/event_" + str(args.event_id),
        collision_id,
        os.path.join(config['global']['output'], f"event_{args.event_id}", "config.yml")
    )

    # Detect and initialize the modules
    ic_type = config['input'].get('initial_conditions', {}).get('type', 'none').lower()
    overlay_type = config['input'].get('overlay', {}).get('type', 'none').lower()
    preequilibrium_type = config['input'].get('preequilibrium', {}).get('type', 'none').lower()
    hydro_type = config['input'].get('hydrodynamics', {}).get('type', 'none').lower()
    particlization_type = config['input'].get('particlization', {}).get('type', 'none').lower()
    afterburner_type = config['input'].get('afterburner', {}).get('type', 'none').lower()
    analysis_type = config['input'].get('analysis', {}).get('type', 'none').lower()

    #report the simulation chain stages and how it will be executed
    print(f"Running simulation chain for event {args.event_id}:")
    print(f"Initial Condition: {ic_type}")
    print(f"Overlay: {overlay_type}")
    print(f"Preequilibrium: {preequilibrium_type}")
    print(f"Hydrodynamics: {hydro_type}")
    print(f"Particlization: {particlization_type}")
    print(f"Afterburner: {afterburner_type}")
    print(f"Analysis: {analysis_type}")

    if ic_type == 'trento':
        initial_condition = TrentoInitialCondition(config, db_connection)
    elif ic_type == 'ampt':
        initial_condition = AmptInitialCondition(config, db_connection)
    elif ic_type == 'none':
        initial_condition = NoneInitialCondition(config, db_connection)
        config['input']['initial_conditions']['type'] = None
    else:
        raise ValueError(f"Unknown initial condition type: {ic_type}")

    initial_condition.validate()
    initial_condition.run(args.event_id)
    update_ic_type(db_connection, args.event_id, ic_type)
    centrality_estimator = initial_condition.get_centrality_estimator()
    update_event_centrality_estimator(db_connection, args.event_id, centrality_estimator)
    # Detect overlay automatically


    if overlay_type == 'iccing':
        overlay_stage = ICCINGOverlay(config, db_connection)
    elif overlay_type == 'amptgenesis':
        overlay_stage = AmptGenesisOverlay(config, db_connection)
    elif overlay_type == 'none':
        overlay_stage = NoneOverlay(config, db_connection)
        config['input']['overlay']['type'] = None
    else:
        raise ValueError(f"Unknown overlay type: {overlay_type}")

    # Run overlay stage if applicable
    overlay_stage.validate(args.event_id)
    overlay_stage.run(args.event_id)
    update_overlay_type(db_connection, args.event_id, overlay_type)


    if preequilibrium_type == 'freestreaming':
        preequilibrium_stage = Freestreaming(config, db_connection)
    elif preequilibrium_type == 'none':
        preequilibrium_stage = NonePreequilibrium(config, db_connection)
        config['input']['preequilibrium']['type'] = None
    else:
        raise ValueError(f"Unknown preequilibrium type: {preequilibrium_type}")
    preequilibrium_stage.validate(args.event_id)
    preequilibrium_stage.run(args.event_id)
    update_preequilibrium_type(db_connection, args.event_id, preequilibrium_type)


    if hydro_type == 'ccake':
        hydro_stage = CCAKEHydro(config, db_connection)
    #elif hydro_type == 'music':
    #    hydro_stage = MusicHydro(config, db_connection)
    elif hydro_type == 'none':
        hydro_stage = NoneHydro(config, db_connection)
        config['input']['hydrodynamics']['type'] = None
    else:
        raise ValueError(f"Unknown hydro type: {hydro_type}")
        

    hydro_stage.validate(args.event_id)
    hydro_stage.run(args.event_id)
    update_hydro_type(db_connection, args.event_id, hydro_type)
    # Update centrality_estimator in the database

    if particlization_type == 'is3d':
        particlization_stage = iS3DParticlization(config, db_connection)
    elif particlization_type == 'bqssampler':
        particlization_stage = BQSSamplerParticlization(config, db_connection)
    elif particlization_type == 'analytical':
        particlization_stage = AnalyticalParticlization(config, db_connection)
    elif particlization_type == 'none':
        particlization_stage = NoneParticlization(config, db_connection)
        config['input']['particlization']['type'] = None
    else:
        raise ValueError(f"Unknown particlization type: {particlization_type}")
    

    particlization_stage.validate(args.event_id)
    particlization_stage.run(args.event_id)

    update_particlization_type(db_connection, args.event_id, particlization_type)



    if afterburner_type == 'none':
        afterburner_stage = NoneAfterburner(config, db_connection)
        config['input']['afterburner']['type'] = None
    elif afterburner_type == 'smash':
        afterburner_stage = SMASHAfterburner(config, db_connection)
    elif afterburner_type == 'afterdecays':
        afterburner_stage = AfterdecaysAfterburner(config, db_connection)
    else:
        raise ValueError(f"Unknown afterburner type: {afterburner_type}")
    
    afterburner_stage.validate(args.event_id)
    afterburner_stage.run(args.event_id)

    update_afterburner_type(db_connection, args.event_id, afterburner_type)



    if analysis_type == 'none':
        analysis_stage = NoneAnalysis(config, db_connection)
        config['input']['analysis']['type'] = None
    elif analysis_type == 'qvector_writter':
        analysis_stage = QVectorWritterAnalysis(config, db_connection)

    else:
        raise ValueError(f"Unknown analysis type: {analysis_type}")


    analysis_stage.validate(args.event_id)
    analysis_stage.run(args.event_id)

    update_analysis_type(db_connection, args.event_id, analysis_type)

    #remove tmp
    shutil.rmtree(os.path.join(config['global']['tmp'], f"event_{args.event_id}"))

    print("Cleaning up temporary files.")
    print("All stages completed successfully, results stored in " + config['global']['output'] + "/event_" + str(args.event_id) + ". Metadata stored in " + args.db_path)

if __name__ == "__main__":
    main()
