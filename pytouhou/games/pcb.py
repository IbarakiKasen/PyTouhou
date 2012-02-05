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
from pytouhou.game.bullettype import LaserType
from pytouhou.game.itemtype import ItemType
from pytouhou.game.player import Player
from pytouhou.game.orb import Orb

from math import pi


class PCBGame(Game):
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
            laser_types = [] #TODO

        if not item_types:
            item_types = [ItemType(etama3, 0, 7), #Power
                          ItemType(etama3, 1, 8), #Point
                          ItemType(etama3, 2, 9), #Big power
                          ItemType(etama3, 3, 10), #Bomb
                          ItemType(etama3, 4, 11), #Full power
                          ItemType(etama3, 5, 12), #1up
                          ItemType(etama3, 6, 13)] #Star

        players = [PCBPlayer(state, self, resource_loader) for state in player_states]

        Game.__init__(self, resource_loader, players, stage, rank, difficulty,
                      bullet_types, laser_types, item_types, nb_bullets_max,
                      width, height, prng)



class PCBPlayer(Player):
    def __init__(self, state, game, resource_loader):
        number = '%d%s' % (state.character // 2, 'b' if state.character % 2 else 'a')
        self.sht = resource_loader.get_sht('ply0%s.sht' % number)
        self.focused_sht = resource_loader.get_sht('ply0%ss.sht' % number)
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
        return self.orbs


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

