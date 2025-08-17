"""
Datastore metadata sync scenario

Demonstrates that VectorClockBroker safely initializes and syncs datastore
location mappings across peers, preventing attribute errors and ensuring
union of locations.

Run:
  PYTHONPATH=. python3 rec/scenario/datastore_metadata_sync_scenario.py
"""
from __future__ import annotations

import time

from rec.Phase3_Core_Implementation.vector_clock_broker import VectorClockBroker


def main():
    b1 = VectorClockBroker("broker_ds_1")
    b2 = VectorClockBroker("broker_ds_2")
    b1.register_peer_broker("broker_ds_2", b2)
    b2.register_peer_broker("broker_ds_1", b1)

    b1.start(); b2.start()

    # Initially empty mappings should not raise
    snap1 = b1.get_metadata_snapshot()
    snap2 = b2.get_metadata_snapshot()
    print("initial_empty_ok:", isinstance(snap1.datastore_locations, dict) and isinstance(snap2.datastore_locations, dict))

    # Seed datastore mappings on b1 and b2
    b1.datastore_mappings["k1"] = ["dsA"]
    b2.datastore_mappings["k1"] = ["dsB"]
    b2.datastore_mappings["k2"] = ["dsC"]

    # Allow sync loop to run (interval ~3s)
    time.sleep(4)

    # After sync, both brokers should have union for shared keys and presence of k2
    print("b1_maps:", b1.datastore_mappings)
    print("b2_maps:", b2.datastore_mappings)
    union_ok = set(b1.datastore_mappings.get("k1", [])) == set(["dsA", "dsB"]) and \
               set(b2.datastore_mappings.get("k1", [])) == set(["dsA", "dsB"]) and \
               "k2" in b1.datastore_mappings and "k2" in b2.datastore_mappings
    print("union_ok:", union_ok)

    b1.stop(); b2.stop()


if __name__ == "__main__":
    main()
