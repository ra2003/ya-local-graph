# -*- coding: utf-8 -*-

import logging

from app.config import SHORT_GRAPH_FILE, FULL_GRAPH_FILE
from app.model import fetch_graph_short, fetch_graph_full


def save_gml(name, nodes, edges, directed=True):
    logging.info('save fetch genre short %d %d', len(nodes), len(edges))
    f = open(name, 'w+')
    content = ['graph [']

    if directed:
        content.append('    directed 1')

    for id, attrs in nodes.items():
        content.append('    node [')
        content.append('        id %d' % id)
        for name, val in attrs.items():
            content.append('        %s "%s"' % (name, val.replace('"', '\'')))
        content.append('    ]')

    for from_id, to_id in edges:
        content.append('    edge [')
        content.append('        source %d' % from_id)
        content.append('        target %d' % to_id)
        content.append('    ]')

    content.append(']')

    f.write("\n".join(content))
    f.close()


def task():
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')

    nodes, edges = fetch_graph_short()
    logging.info('fetch short %d %d', len(nodes), len(edges))
    save_gml(SHORT_GRAPH_FILE, nodes, edges)
    logging.info('graph export complete')

    nodes, edges = fetch_graph_full()
    logging.info('fetch full %d %d', len(nodes), len(edges))
    save_gml(FULL_GRAPH_FILE, nodes, edges)
    logging.info('graph export complete')
