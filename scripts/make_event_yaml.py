#!/usr/bin/env python3
"""Generate a per-event chain config from a template by overriding a few
top-level paths — the safe way to template a YAML config (parse + dump,
rather than sed/grep on YAML text, which breaks silently on formatting
changes). Used by submit_chain_ampt.sh for the AMPT-freeze-out-surface ->
particlization restart pattern; general enough for other partial-chain
restarts (see examples/README.md).

Usage:
    python make_event_yaml.py <template.yml> <out.yml>
        [--output DIR] [--tmp DIR] [--particlization-input-file PATH]

Only the given overrides are applied; everything else in the template is
preserved as-is (not schema-validated — this is a templating step, not a
config; validate the result with wrapper/utils/input_file.py if needed).
Prints the template's own global.tmp value to stdout, so callers can find
and clean up the scratch tree it points at without re-parsing YAML.
"""
import argparse

import yaml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('template')
    parser.add_argument('out_yaml')
    parser.add_argument('--output', help="override global.output")
    parser.add_argument('--tmp', help="override global.tmp")
    parser.add_argument('--particlization-input-file',
                        help="override input.particlization.parameters.input_file "
                             "(e.g. a freeze_out.dat to restart from)")
    args = parser.parse_args()

    with open(args.template) as f:
        config = yaml.safe_load(f)

    print(config['global']['tmp'])

    if args.output:
        config['global']['output'] = args.output
    if args.tmp:
        config['global']['tmp'] = args.tmp
    if args.particlization_input_file:
        config['input']['particlization']['parameters']['input_file'] = \
            args.particlization_input_file

    with open(args.out_yaml, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)


if __name__ == '__main__':
    main()
