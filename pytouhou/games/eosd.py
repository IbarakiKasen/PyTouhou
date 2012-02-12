# -*- encoding: utf-8 -*-
##
## Copyright (C) 2011 Emmanuel Gil Peyrot <linkmauve@linkmauve.fr>
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published
## by the Free Software Foundation; version 3 only.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##

from pytouhou.utils.interpolator import Interpolator

from pytouhou.game.game import Game
from pytouhou.game.bullettype import BulletType
from pytouhou.game.lasertype import LaserType
from pytouhou.game.itemtype import ItemType
from pytouhou.game.player import Player
from pytouhou.game.orb import Orb

from math import pi


SQ2 = 2. ** 0.5 / 2.


class EoSDGame(Game):
    def __init__(self, resource_loader, player_states, stage, rank, difficulty,
                 bullet_types=None, laser_types=None, item_types=None,
                 nb_bullets_max=640, width=384, height=448, prng=None):

        if not bullet_types:
            etama3 = resource_loader.get_anm_wrapper(('etama3.anm',))
            etama4 = resource_loader.get_anm_wrapper(('etama4.anm',))
            bullet_types = [BulletType(etama3, 0, 11, 14, 15, 16, hitbox_size=4),
                            BulletType(etama3, 1, 12, 17, 18, 19, hitbox_size=6),
                            BulletType(etama3, 2, 12, 17, 18, 19, hitbox_size=4),
                            BulletType(etama3, 3, 12, 17, 18, 19, hitbox_size=6),
                            BulletType(etama3, 4, 12, 17, 18, 19, hitbox_size=5),
                            BulletType(etama3, 5, 12, 17, 18, 19, hitbox_size=4),
                            BulletType(etama3, 6, 13, 20, 20, 20, hitbox_size=16),
                            BulletType(etama3, 7, 13, 20, 20, 20, hitbox_size=11),
                            BulletType(etama3, 8, 13, 20, 20, 20, hitbox_size=9),
                            BulletType(etama4, 0, 1, 2, 2, 2, hitbox_size=32)]

        if not laser_types:
            laser_types = [LaserType(etama3, 9),
                           LaserType(etama3, 10)]

        if not item_types:
            item_types = [ItemType(etama3, 0, 7), #Power
                          ItemType(etama3, 1, 8), #Point
                          ItemType(etama3, 2, 9), #Big power
                          ItemType(etama3, 3, 10), #Bomb
                          ItemType(etama3, 4, 11), #Full power
                          ItemType(etama3, 5, 12), #1up
                          ItemType(etama3, 6, 13)] #Star

        player_face = player_states[0].character // 2
        enemy_face = [('face03a.anm', 'face03b.anm'),
                      ('face05a.anm',),
                      ('face06a.anm', 'face06b.anm'),
                      ('face08a.anm', 'face08b.anm'),
                      ('face09a.anm', 'face09b.anm'),
                      ('face09b.anm', 'face10a.anm', 'face10b.anm'),
                      ('face08a.anm', 'face12a.anm', 'face12b.anm', 'face12c.anm')]
        self.msg = resource_loader.get_msg('msg%d.dat' % stage)
        self.msg_anm_wrapper = resource_loader.get_anm_wrapper2(('face0%da.anm' % player_face,
                                                                 'face0%db.anm' % player_face,
                                                                 'face0%dc.anm' % player_face)
                                                                + enemy_face[stage - 1],
                                                                (0, 2, 4, 8, 10, 11, 12))

        characters = resource_loader.get_eosd_characters()
        players = [EoSDPlayer(state, self, resource_loader, characters[state.character]) for state in player_states]

        Game.__init__(self, resource_loader, players, stage, rank, difficulty,
                      bullet_types, laser_types, item_types, nb_bullets_max,
                      width, height, prng)



class EoSDPlayer(Player):
    def __init__(self, state, game, resource_loader, character):
        self.sht = character[0]
        self.focused_sht = character[1]
        anm_wrapper = resource_loader.get_anm_wrapper(('player0%d.anm' % (state.character // 2),))
        self.anm_wrapper = anm_wrapper

        Player.__init__(self, state, game, anm_wrapper)

        self.orbs = [Orb(self.anm_wrapper, 128, self.state, None),
                     Orb(self.anm_wrapper, 129, self.state, None)]

        self.orbs[0].offset_x = -24
        self.orbs[1].offset_x = 24

        self.orb_dx_interpolator = None
        self.orb_dy_interpolator = None


    def start_focusing(self):
        self.orb_dx_interpolator = Interpolator((24,), self._game.frame,
                                                (8,), self._game.frame + 8,
                                                lambda x: x ** 2)
        self.orb_dy_interpolator = Interpolator((0,), self._game.frame,
                                                (-32,), self._game.frame + 8)
        self.state.focused = True


    def stop_focusing(self):
        self.orb_dx_interpolator = Interpolator((8,), self._game.frame,
                                                (24,), self._game.frame + 8,
                                                lambda x: x ** 2)
        self.orb_dy_interpolator = Interpolator((-32,), self._game.frame,
                                                (0,), self._game.frame + 8)
        self.state.focused = False


    def objects(self):
        return self.orbs if self.state.power >= 8 else []


    def update(self, keystate):
        Player.update(self, keystate)

        if self.death_time == 0 or self._game.frame - self.death_time > 60:
            if self.orb_dx_interpolator:
                self.orb_dx_interpolator.update(self._game.frame)
                dx, = self.orb_dx_interpolator.values
                self.orbs[0].offset_x = -dx
                self.orbs[1].offset_x = dx
            if self.orb_dy_interpolator:
                self.orb_dy_interpolator.update(self._game.frame)
                dy, = self.orb_dy_interpolator.values
                self.orbs[0].offset_y = dy
                self.orbs[1].offset_y = dy

        for orb in self.orbs:
            orb.update()

