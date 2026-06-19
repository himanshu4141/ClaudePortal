"""Glue between snapshots, physical inputs, and the pet on screen.

Replaces the old MoodController. Each loop tick it polls inputs (shake/face-down/
buttons), feeds them to the BuddyState machine, applies pet selection, then renders
the resolved state into the BuddyScreen. Device-only (inputs imports board).
"""

import time

import buddy_state as bs
import inputs as inputs_mod


class BuddyController:
    def __init__(self, buddy_screen):
        self.screen = buddy_screen
        self.state = bs.BuddyState()
        self.selector = inputs_mod.PetSelector()
        self.inputs = inputs_mod.Inputs()
        self.screen.engine.set_pet(self.selector.load_module())

    def update_snapshot(self, snapshot):
        self.state.update_snapshot(snapshot)

    def tick(self):
        now = time.monotonic()
        shaken, face_down, pet_delta = self.inputs.poll()
        if shaken:
            self.state.on_shake(now)
        self.state.set_orientation(face_down, now)
        if pet_delta:
            self.selector.nudge(pet_delta)
            self.screen.engine.set_pet(self.selector.load_module())
            print("buddy: pet -> {}".format(self.selector.name()))
        state = self.state.tick(now)
        self.screen.render(state, self.state.energy, now)
