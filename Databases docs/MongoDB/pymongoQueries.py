# Author: Group 6

from bson import SON
from pymongo import MongoClient, GEOSPHERE
from datetime import datetime
import pandas as pd
import folium
from folium import plugins


def get_session(db_name):
    """
    :param db_name: Nombre de la base de datos de los incidentes y los distritos
    :return: Objeto de tipo DataBase con una conexión a la base de datos local
    """
    client = MongoClient()
    db = client[db_name]
    return db


def create_indexes(db):
    """
    GEOSPHERE: para procesar coordinadas esféricas
    :param db: Añade un índice sobre los campos que contienen información geoespacial
    """
    db.incidents.create_index([("Location", GEOSPHERE)])
    db.neighbours.create_index([("the_geom", GEOSPHERE)])


def first_query(db):
    """
    :param db: referencia a la sesión de la bd
    :return: Esta función obtiene los incidentes que están a una distancia máximo de 1km
    desde un punto representado por coordinadas geográficas en formato geojson
    """
    # Montamos la query
    query_incidents = {"Location":
        {"$geoIntersects":
            {"$geometry": SON([
                ("type", "Point"),
                ("coordinates", [-122.42158168136999, 37.7617007179518])
            ])}
        }
    }
    # Ejecutamos la querry sobre la colección de incidencias
    query_results = db.incidents.find(query_incidents)
    return query_results


def second_query(db):
    """
    :param db: referencia a la sesión de la bd
    :return: devuelve el distrito que contiene las coordinadas usadas en el
    operado de intersección
    """
    # Montamos la query
    query_distrito = {"Location":
        {"$geoIntersects":
            {"$geometry": SON([
                ("type", "Point"),
                ("coordinates", [-122.42158168136999, 37.7617007179518])])
            }
        }
    }
    # Ejecutamos la querry sobre la colección de incidencias
    query_results = db.neighbours.find_one(query_distrito)
    return query_results


def third_query(db):
    """
    :param db: referencia a la sesión de la bd
    :return: Devuelve el todos los incidentes que de un distrito, usando
    operadores geo-espaciales, la consulta se realiza en fases sobre las dos
    colecciones, primero encontramos el distrito, y luego buscamos todos los
    incidentes que tienen las coordinadas dentro del polígono
    """
    # Empezamos con el distrito
    query_distrito = {"the_geom": {"$geoIntersects": {
        "$geometry": SON([("type", "Point"), ("coordinates", [-122.42158168136999, 37.7617007179518])])}}}
    distrito = db.neighbours.find_one(query_distrito)
    # Ahora encontramos los incidentes
    query_incidents = {"Location": {"$geoWithin": {"$geometry": distrito['the_geom']}}}
    query_results = db.incidents.find(query_incidents)
    return query_results


def since_february(db):
    """
    :param db: referencia a la sesión de la bd
    :return: Devuelve los incidentes que han ocurrido desde febrero de 2018
    """
    fecha = datetime(2018, 2, 1)
    incidents = db.incidents.find({"Date": {"$gt": fecha}})
    df = pd.DataFrame(list(incidents))
    return df


def date_querry(op, sdate, edate):
    """
    :param opr: operador B: between dates, L: less than, G: greater than
    :return: devuelve el filtro de la consulta según lo que se recibe por parámetro
    en op
    """
    switcher = {
        'B': {"Date": {"$gte": sdate, "$lte": edate}},  # Between
        'GE': {"Date": {"$gte": sdate}},              # Greater than or equal
        'LE': {"Date": {"$lte": sdate}},              # less than or equal
    }
    return switcher.get(op)


def generic_date_search(db, op, sdate, *args, **kwargs):
    """
    :param db: referencia a la sesión de bd
    :param op: operador para seleccionar
    :param sdate: primera fecha, mandaterio
    :param args:
    :param kwargs: Contiene argumento opcional de la seguna fecha
    :return: incidentes que cumplen con el filtro sobre fechas
    """
    edate = kwargs.get('edate', None)
    if not edate is None:
        query = date_querry(op, sdate, edate)
    else:
        query = date_querry(op, sdate, None)
    query_results = db.incidents.find(query)
    return query_results


def draw_map(feb):
    incid_map = folium.Map(location=[-122.42158168136999, 37.7617007179518], zoom_start=11, tiles='Stamen Terrain')
    marker_cluster = plugins.MarkerCluster().add_to(incid_map)
    for name, row in feb.iterrows():
        folium.Marker([row["Y"], row["X"]], popup=row["Descript"]).add_to(marker_cluster)
    incid_map.save('stops.html')


def draw_heatmap(df):
    heat_map = folium.Map(location=[-122.42158168136999, 37.7617007179518], zoom_start=11, tiles='Stamen Terrain')
    heat_map.add_child(plugins.HeatMap([[row["Y"], row["X"]] for name, row in df.iterrows()]))
    heat_map.save('stops.html')


if __name__ == "__main__":
    sfdb = get_session("san_francisco_incidents")  # Obtenemos la bd con su nombre
    # create_indexes(sfdb)  # Nos aseguramos de que existan indíces geo-espaciales

    fq = first_query(sfdb)
    sq = second_query(sfdb)
    tq = third_query(sfdb)

    feb = since_february(sfdb)  # Consulta específica a una fecha
    fecha1 = datetime(2017, 12, 1)
    fecha2 = datetime(2017, 12, 31)
    results = generic_date_search(sfdb,'B', fecha1, edate=fecha2)
    resultsdf = pd.DataFrame(list(results))
    draw_map(feb)
    draw_heatmap(resultsdf)
