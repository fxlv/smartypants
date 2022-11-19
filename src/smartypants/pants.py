import click
import worker
import config
import pubsub
import zabbix
import time

from smartypants.statekeeper import StateKeeper


@click.command()
def run():
    """Runs the Smartypants daemon"""
    c = config.Config()
    z = zabbix.Zabbix(c)
    s = StateKeeper()
    try:
        pubsub_thread = pubsub.run_pubsub(c, s)
        worker.Worker(c, pubsub_thread.q, s).run()
        pubsub_thread.join()
    except KeyboardInterrupt:
        pubsub_thread.stop_event.set()
        # now wait for the thread to finish
        time.sleep(1)


if __name__ == "__main__":
    run()
