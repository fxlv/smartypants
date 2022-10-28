import click
import worker
import config
import pubsub
import zabbix
import time


@click.command()
def run():
    """Runs the Smartypants daemon"""
    c = config.Config()
    z = zabbix.Zabbix(c)
    try:
        pubsub_thread = pubsub.run_pubsub(c)
        worker.Worker(c, pubsub_thread.q).run()
        pubsub_thread.join()
    except KeyboardInterrupt:
        pubsub_thread.stop_event.set()
        # now wait for the thread to finish
        time.sleep(1)


if __name__ == "__main__":
    run()
