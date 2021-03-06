# -*- coding: utf-8 -*-

from peewee import PostgresqlDatabase, Model, CharField, IntegerField, IntegrityError, BooleanField, CompositeKey, \
    RawQuery

from app.config import DB_USER, DB_PSWD, DB_NAME, EXPORT_LIMIT, COLOR_BOTH, COLOR_METAL, COLOR_ROCK

db = PostgresqlDatabase(DB_NAME, user=DB_USER, password=DB_PSWD, autorollback=True)
db.connect()


class Artist(Model):
    id = IntegerField(primary_key=True)
    name = CharField()
    similar_crawled = BooleanField(index=True, default=False)
    need_crawl_similar = BooleanField(index=True, default=False)
    is_primary = BooleanField(index=True, default=False)
    degree_input = IntegerField()
    degree_output = IntegerField()

    class Meta:
        database = db


class Similar(Model):
    from_id = IntegerField()
    to_id = IntegerField()
    position = IntegerField()

    class Meta:
        database = db
        primary_key = CompositeKey('from_id', 'to_id')


class Genre(Model):
    id = IntegerField(primary_key=True)
    genre = CharField(unique=True)

    class Meta:
        database = db


class ArtistGenre(Model):
    artist_id = IntegerField()
    genre_id = IntegerField()

    class Meta:
        database = db
        primary_key = CompositeKey('artist_id', 'genre_id')
        db_table = 'artist_genre'


def get_artists_for_crawling_similar():
    return Artist.select().where(Artist.need_crawl_similar == True, Artist.similar_crawled == False).order_by(
        Artist.is_primary.desc())


def save_new_artist(artist_id, name, is_primary=False):
    try:
        Artist.create(id=artist_id, name=name, similar_crawled=False, is_primary=is_primary)
        return True
    except IntegrityError:
        if is_primary:
            Artist.update(is_primary=True).where(Artist.id == artist_id).execute()
        return False


def clear_similar_edges(from_id):
    Similar.delete().where(Similar.from_id == from_id).execute()


def get_similar(from_id):
    return Similar.select().where(Similar.from_id == from_id)


def save_similar_edge(from_id, to_id, pos):
    try:
        Similar.create(from_id=from_id, to_id=to_id, position=pos)
        return True
    except IntegrityError:
        return False


def set_to_crawling_similar(genres):
    genre_subquery = Genre.select(Genre.id).where(Genre.genre << genres)
    artist_id_subquery = ArtistGenre.select(ArtistGenre.artist_id).where(ArtistGenre.genre_id << genre_subquery)
    q = Artist.update(need_crawl_similar=True).where(Artist.id << artist_id_subquery)
    q.execute()


def update_crawled_similar_state(artist_id, state):
    q = Artist.update(similar_crawled=state).where(Artist.id == artist_id)
    q.execute()


def add_genre(name):
    return Genre.get_or_create(genre=name)[0].id


def get_genres():
    res = Genre.select()
    return {g.genre: g.id for g in res}


def update_artist_genres(artist_id, genres_id):
    ArtistGenre.delete().where(ArtistGenre.artist_id == artist_id).execute()
    for g in genres_id:
        ArtistGenre.create(artist_id=artist_id, genre_id=g)


def fetch_top_by_genre(genre_ids=None, reverse=False, limit=10):
    where = ''
    if genre_ids:
        in_ = 'NOT IN' if reverse else 'IN'
        where = 'WHERE id %s (SELECT DISTINCT artist_id FROM artist_genre WHERE genre_id IN (%s)) ' \
                % (in_, ','.join([str(i) for i in genre_ids]))

    rq = RawQuery(Similar,
                  'SELECT name, degree_input '
                  'FROM "artist" %s '
                  'ORDER BY degree_input DESC '
                  'LIMIT %d' % (where, limit))
    return [(i.name, i.degree_input) for i in rq.execute()]


def fetch_graph_custom(rock_ids, metal_ids, max_position=100, primary=True):
    rock_in = ','.join([str(i) for i in rock_ids])
    metal_in = ','.join([str(i) for i in metal_ids])
    all_in_ = ','.join([rock_in, metal_in])
    primary_condition = 'a1.is_primary = True AND a2.is_primary = True AND' if primary else ''

    rq = RawQuery(Similar, 'SELECT from_id, a1.name as from_label, to_id, a2.name as to_label, '
                           'a1.degree_input as from_degree, a2.degree_input as to_degree, '
                           'CASE WHEN (SELECT COUNT(*) FROM artist_genre '
                           'WHERE genre_id IN (%s) AND artist_id = from_id) > 0 '
                           'THEN 1 ELSE 0 END AS from_is_rock, '
                           'CASE WHEN (SELECT COUNT(*) FROM artist_genre '
                           'WHERE genre_id IN (%s) AND artist_id = from_id) > 0 '
                           'THEN 1 ELSE 0 END AS from_is_metal, '
                           'CASE WHEN (SELECT COUNT(*) FROM artist_genre '
                           'WHERE genre_id IN (%s) AND artist_id = to_id) > 0 '
                           'THEN 1 ELSE 0 END AS to_is_rock, '
                           'CASE WHEN (SELECT COUNT(*) FROM artist_genre '
                           'WHERE genre_id IN (%s) AND artist_id = to_id) > 0 '
                           'THEN 1 ELSE 0 END AS to_is_metal '
                           'FROM "similar" '
                           'JOIN "artist" a1 ON (from_id = a1.id) '
                           'JOIN "artist" a2 ON (to_id = a2.id) '
                           'WHERE %s position < %d'
                           'AND from_id IN (SELECT DISTINCT artist_id FROM artist_genre WHERE genre_id IN (%s)) '
                           'AND to_id IN (SELECT DISTINCT artist_id FROM artist_genre WHERE genre_id  IN (%s)) '
                           'LIMIT %d' % (rock_in, metal_in, rock_in, metal_in, primary_condition, max_position,
                                         all_in_, all_in_, EXPORT_LIMIT))

    def select_color(is_rock, is_metal):
        if is_rock and is_metal:
            return COLOR_BOTH
        elif is_rock:
            return COLOR_ROCK
        elif is_metal:
            return COLOR_METAL
        else:
            return 'grey'

    nodes = {}
    edges = []
    for obj in rq.execute():
        nodes[obj.from_id] = {'label': obj.from_label, 'color': select_color(obj.from_is_rock, obj.from_is_metal),
                              'size': obj.from_degree}
        nodes[obj.to_id] = {'label': obj.to_label, 'color': select_color(obj.to_is_rock, obj.to_is_metal),
                            'size': obj.to_degree}
        edges.append((obj.from_id, obj.to_id))
    return nodes, edges


def fetch_graph_primary(genre_ids, max_position=100, color='red'):
    """Return primary genre graph w/o single nodes"""

    in_ = ','.join([str(i) for i in genre_ids])

    rq = RawQuery(Similar, 'SELECT from_id, a1.name as from_label, to_id, a2.name as to_label, '
                           'a1.degree_input as from_degree, a2.degree_input as to_degree '
                           'FROM "similar" '
                           'JOIN "artist" a1 ON (from_id = a1.id) '
                           'JOIN "artist" a2 ON (to_id = a2.id) '
                           'WHERE a1.is_primary = True AND a2.is_primary = True AND position < %d'
                           'AND from_id IN (SELECT DISTINCT artist_id FROM artist_genre WHERE genre_id IN (%s)) '
                           'AND to_id IN (SELECT DISTINCT artist_id FROM artist_genre WHERE genre_id  IN (%s)) '
                           'LIMIT %d' % (max_position, in_, in_, EXPORT_LIMIT))
    nodes = {}
    edges = []
    for obj in rq.execute():
        nodes[obj.from_id] = {'label': obj.from_label, 'color': color, 'size': obj.from_degree}
        nodes[obj.to_id] = {'label': obj.to_label, 'color': color, 'size': obj.to_degree}
        edges.append((obj.from_id, obj.to_id))
    return nodes, edges


def fetch_graph_full(genre_ids, color='red', max_position=100):
    """Return full graph w/o single nodes"""

    in_ = ','.join([str(i) for i in genre_ids])

    rq = RawQuery(Similar, 'SELECT from_id, a1.name as from_label, to_id, a2.name as to_label, '
                           'a1.degree_input as from_degree, a2.degree_input as to_degree '
                           'FROM "similar" '
                           'JOIN "artist" a1 ON (from_id = a1.id) '
                           'JOIN "artist" a2 ON (to_id = a2.id) '
                           'WHERE position < %d AND '
                           'from_id IN (SELECT DISTINCT artist_id FROM artist_genre WHERE genre_id IN (%s)) '
                           'AND to_id IN (SELECT DISTINCT artist_id FROM artist_genre WHERE genre_id  IN (%s)) '
                           'LIMIT %d' % (max_position, in_, in_, EXPORT_LIMIT))
    nodes = {}
    edges = []
    for obj in rq.execute():
        nodes[obj.from_id] = {'label': obj.from_label, 'color': color, 'size': obj.from_degree}
        nodes[obj.to_id] = {'label': obj.to_label, 'color': color, 'size': obj.to_degree}
        edges.append((obj.from_id, obj.to_id))
    return nodes, edges


def update_degree():
    rq = RawQuery(Similar, 'UPDATE "artist" SET '
                           'degree_output = (SELECT COUNT(*) FROM "similar" WHERE from_id = id), '
                           'degree_input = (SELECT COUNT(*) FROM "similar" WHERE to_id = id)')
    rq.execute()
