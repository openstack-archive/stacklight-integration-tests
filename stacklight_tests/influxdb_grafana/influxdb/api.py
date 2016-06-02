import influxdb


def get_nova_instance_creation_time_metrics(url, db_name, env_name,
                                            user, password,
                                            interval="1h",
                                            time_quantum="20m"):
    proto, host, port = url.replace('/', '').split(':')
    client = influxdb.InfluxDBClient(host=host, port=port, database=db_name,
                                     username=user, password=password)
    query = ('SELECT mean("value") '
             'FROM "openstack_nova_instance_creation_time" '
             'WHERE "environment_label" = \'{env_name}\' '
             'AND time > now() - {interval} '
             'GROUP BY time({quantum})'.format(interval=interval,
                                               quantum=time_quantum,
                                               env_name=env_name))
    result = client.query(query=query)
    return dict(result.raw['series'][0]['values'])
