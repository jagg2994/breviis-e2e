"""Flujos impl:custom del manifiesto — registro por ID de flujo."""

from flows.public_booking import flow_c10
from flows.admin_bookings import flow_a6, flow_a7, flow_a9

CUSTOM = {
    "C10": flow_c10,
    "A6": flow_a6,
    "A7": flow_a7,
    "A9": flow_a9,
}
