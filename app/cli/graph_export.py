# -*- coding: utf-8 -*-

import logging

from app.cli import graph_path, gml_name, graph_index
from app.cli.graph_plot import clear_cache
from app.config import ALL_ROCK_GENRE, ROCK_GENRES, ALL_METAL_GENRE, METAL_GENRES, ROCK_AND_METAL_GENRE, COLOR_METAL, \
    COLOR_ROCK
from app.model import fetch_graph_primary, fetch_graph_full, get_genres, fetch_graph_custom, update_degree, \
    fetch_top_by_genre


def save_gml(genre_name, nodes, edges, full=False):
    logging.info('save graph %d %d', len(nodes), len(edges))

    g_name = graph_path(graph_index(genre_name, full))
    f_name = gml_name(g_name)
    f = open(f_name, 'w+')

    content = ['graph [', '    directed 1']
    for node_id, attrs in nodes.items():
        content.append('    node [')
        content.append('        id %d' % node_id)
        for name, val in attrs.items():
            if isinstance(val, str):
                content.append('        %s "%s"' % (name, val.replace('"', '\'')))
            else:
                content.append('        %s %s' % (name, val))
        content.append('    ]')

    for from_id, to_id in edges:
        content.append('    edge [')
        content.append('        source %d' % from_id)
        content.append('        target %d' % to_id)
        content.append('    ]')

    content.append(']')

    f.write("\n".join(content))
    f.close()

    clear_cache(g_name)


def save_csv(name, pairs):
    with open(graph_path(name) + '.csv', 'w+') as f:
        for p in pairs:
            f.write("%s;%d\n" % p)


def task():
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
    genres = get_genres()
    rock_ids = [str(genres[i]) for i in genres if i in ROCK_GENRES]
    metal_ids = [str(genres[i]) for i in genres if i in METAL_GENRES]

    def _export(genre_ids, genre_name, color):
        logging.info('export start %s %s', genre_name, genre_ids)
        nodes, edges = fetch_graph_primary(genre_ids, color=color)
        save_gml(genre_name, nodes, edges)
        nodes, edges = fetch_graph_full(genre_ids, color=color)
        save_gml(genre_name, nodes, edges, full=True)
        logging.info('end')

    update_degree()
    logging.info('update degree')

    for genre_name in METAL_GENRES:
        genre_ids = [genres[genre_name]]
        _export(genre_ids, genre_name, COLOR_METAL)

    for genre_name in ROCK_GENRES:
        genre_ids = [genres[genre_name]]
        _export(genre_ids, genre_name, COLOR_ROCK)

    custom_pairs = [(rock_ids, ALL_ROCK_GENRE, COLOR_ROCK),
                    (metal_ids, ALL_METAL_GENRE, COLOR_METAL)]
    for ids, name, color in custom_pairs:
        _export(ids, name, color)

    # custom export colorized graph
    logging.info('export customs full start %s %s', ROCK_AND_METAL_GENRE, rock_ids + metal_ids)
    nodes, edges = fetch_graph_custom(rock_ids, metal_ids, primary=False)
    save_gml(ROCK_AND_METAL_GENRE, nodes, edges, full=True)
    logging.info('end')

    # export top by degree input
    logging.info('export degree top')
    rock_top = fetch_top_by_genre(rock_ids)
    save_csv('rock-top', rock_top)
    metal_top = fetch_top_by_genre(metal_ids)
    save_csv('metal-top', metal_top)
    summary_top = fetch_top_by_genre(rock_ids + metal_ids)
    save_csv('summary-top', summary_top)
    outside_top = fetch_top_by_genre(rock_ids + metal_ids, True)
    save_csv('outside-top', outside_top)
    logging.info('end')


if __name__ == '__main__':
    task()
