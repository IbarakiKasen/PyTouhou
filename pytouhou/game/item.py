# -*- encoding: utf-8 -*-
##
## Copyright (C) 2011 Thibaut Girka <thib@sitedethib.com>
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


from math import cos, sin, atan2, pi

from pytouhou.utils.interpolator import Interpolator


class Item(object):
    def __init__(self, start_pos, _type, item_type, game, angle=pi/2, speed=8., player=None, end_pos=None):
        self._game = game
        self._sprite = item_type.sprite
        self._removed = False
        self._type = _type
        self._item_type = item_type

        self.hitbox_half_size = item_type.hitbox_size / 2.

        self.frame = 0

        self.player = player

        self.x, self.y = start_pos
        self.angle = angle
        self.speed = speed
        dx, dy = cos(angle) * speed, sin(angle) * speed
        self.delta = dx, dy

        if not player:
            #TODO: find the formulae in the binary.
            self.speed_interpolator = None
            if end_pos:
                self.pos_interpolator = Interpolator(start_pos, 0,
                                                     end_pos, 60)
            else:
                self.speed_interpolator = Interpolator((-2.,), 0,
                                                       (0.,), 60)

        self._sprite.angle = angle


    def on_collect(self, player_state):
        old_power = player_state.power

        if self._type == 0 or self._type == 2: # power or big power
            if old_power < 128:
                player_state.power_bonus = 0
                score = 10
                player_state.power += (1 if self._type == 0 else 8)
                if player_state.power > 128:
                    player_state.power = 128
            else:
                bonus = player_state.power_bonus + (1 if self._type == 0 else 8)
                if bonus > 30:
                    bonus = 30
                if bonus < 9:
                    score = (bonus + 1) * 10
                elif bonus < 18:
                    score = (bonus - 8) * 100
                elif bonus < 30:
                    score = (bonus - 17) * 1000
                elif bonus == 30:
                    score = 51200
                player_state.power_bonus = bonus
            player_state.score += score

        elif self._type == 1: # point
            player_state.points += 1
            if player_state.y < 128: #TODO: find the exact poc.
                score = 100000
            else:
                score = 0 #TODO: find the formula.
            player_state.score += score

        elif self._type == 3: # bomb
            if player_state.bombs < 8:
                player_state.bombs += 1

        elif self._type == 4: # full power
            player_state.score += 1000
            player_state.power = 128

        elif self._type == 5: # 1up
            if player_state.lives < 8:
                player_state.lives += 1

        elif self._type == 6: # star
            player_state.score += 500

        if old_power < 128 and player_state.power >= 128:
            #TODO: display “full power”.
            self._game.change_bullets_into_star_items()

        self._removed = True


    def update(self):
        dx, dy = self.delta

        if self.frame == 60:
            self.speed_interpolator = Interpolator((0.,), 60,
                                                   (3.,), 180)

        if self.player is not None:
            self.angle = atan2(self.player.y - self.y, self.player.x - self.x)
            self.x += cos(self.angle) * self.speed
            self.y += sin(self.angle) * self.speed
        elif self.speed_interpolator is None:
            self.pos_interpolator.update(self.frame)
            self.x, self.y = self.pos_interpolator.values
        else:
            self.speed_interpolator.update(self.frame)
            self.speed, = self.speed_interpolator.values
            dx, dy = cos(self.angle) * self.speed, sin(self.angle) * self.speed
            self.delta = dx, dy
            self.x += dx
            self.y += dy

        self.frame += 1

