from django.core.management.base import BaseCommand
from stats.consumer import StatsKafkaConsumer


class Command(BaseCommand):
    help = 'Inicia el consumer de Kafka para estadísticas de jugadores'

    def add_arguments(self, parser):
        parser.add_argument(
            '--bootstrap-servers',
            type=str,
            default='localhost:9092',
            help='Servidores bootstrap de Kafka'
        )
        parser.add_argument(
            '--topic',
            type=str,
            default='player-stats',
            help='Topic de Kafka a consumir'
        )

    def handle(self, *args, **options):
        bootstrap_servers = options['bootstrap_servers']
        topic = options['topic']
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Iniciando consumer en {bootstrap_servers} '
                f'para topic {topic}'
            )
        )
        
        consumer = StatsKafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            topic=topic
        )
        consumer.start()