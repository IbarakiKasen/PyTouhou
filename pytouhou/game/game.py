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


from pytouhou.utils.random import Random

from pytouhou.vm.eclrunner import ECLMainRunner

from pytouhou.game.enemy import Enemy
from pytouhou.game.item import Item
from pytouhou.game.effect import Effect
from pytouhou.game.effect import Particle



class Game(object):
    def __init__(self, resource_loader, players, stage, rank, difficulty,
                 bullet_types, item_types, prng=None, nb_bullets_max=None):
        self.resource_loader = resource_loader

        self.nb_bullets_max = nb_bullets_max
        self.bullet_types = bullet_types
        self.item_types = item_types

        self.players = players
        self.enemies = []
        self.effects = []
        self.bullets = []
        self.cancelled_bullets = []
        self.players_bullets = []
        self.items = []

        self.stage = stage
        self.rank = rank
        self.difficulty = difficulty
        self.difficulty_counter = 0
        self.difficulty_min = 12 if rank == 0 else 10
        self.difficulty_max = 20 if rank == 0 else 32
        self.boss = None
        self.spellcard = None
        self.bonus_list = [0, 0, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0,
                           1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 0, 2]
        self.prng = prng or Random()
        self.frame = 0

        self.enm_anm_wrapper = resource_loader.get_anm_wrapper2(('stg%denm.anm' % stage,
                                                                 'stg%denm2.anm' % stage))
        self.etama4 = resource_loader.get_anm_wrapper(('etama4.anm',))
        ecl = resource_loader.get_ecl('ecldata%d.ecl' % stage)
        self.ecl_runner = ECLMainRunner(ecl, self)

        # See 102h.exe@0x413220 if you think you're brave enough.
        self.deaths_count = self.prng.rand_uint16() % 3
        self.next_bonus = self.prng.rand_uint16() % 8


    def modify_difficulty(self, diff):
        self.difficulty_counter += diff
        while self.difficulty_counter < 0:
            self.difficulty -= 1
            self.difficulty_counter += 100
        while self.difficulty_counter >= 100:
            self.difficulty += 1
            self.difficulty_counter -= 100
        if self.difficulty < self.difficulty_min:
            self.difficulty = self.difficulty_min
        elif self.difficulty > self.difficulty_max:
            self.difficulty = self.difficulty_max


    def drop_bonus(self, x, y, _type, end_pos=None):
        player = self.players[0] #TODO
        if _type > 6:
            return
        item_type = self.item_types[_type]
        item = Item((x, y), _type, item_type, self, end_pos=end_pos)
        self.items.append(item)


    def change_bullets_into_star_items(self):
        player = self.players[0] #TODO
        item_type = self.item_types[6]
        self.items.extend(Item((bullet.x, bullet.y), 6, item_type, self, player=player) for bullet in self.bullets)
        self.bullets = []


    def new_death(self, pos, index):
        anim = {0: 3, 1: 4, 2: 5}[index % 256] # The TB is wanted, if index isn’t in these values the original game crashs.
        self.effects.append(Effect(pos, anim, self.etama4))


    def new_particle(self, pos, color, size, amp):
        self.effects.append(Particle(pos, 7 + 4 * color + self.prng.rand_uint16() % 4, self.etama4, size, amp, self))


    def new_enemy(self, pos, life, instr_type, bonus_dropped, die_score):
        enemy = Enemy(pos, life, instr_type, bonus_dropped, die_score, self.enm_anm_wrapper, self)
        self.enemies.append(enemy)
        return enemy


    def run_iter(self, keystate):
        # 1. VMs.
        self.ecl_runner.run_iter()
        if self.frame % (32*60) == (32*60): #TODO: check if that is really that frame.
            self.modify_difficulty(+100)

        # 2. Filter out destroyed enemies
        self.enemies = [enemy for enemy in self.enemies if not enemy._removed]
        self.effects = [enemy for enemy in self.effects if not enemy._removed]
        self.bullets = [bullet for bullet in self.bullets if not bullet._removed]
        self.cancelled_bullets = [bullet for bullet in self.cancelled_bullets if not bullet._removed]
        self.items = [item for item in self.items if not item._removed]


        # 3. Let's play!
        # In the original game, updates are done in prioritized functions called "chains"
        # We have to mimic this functionnality to be replay-compatible with the official game.

        # Pri 6 is background
        self.update_players(keystate) # Pri 7
        self.update_enemies() # Pri 9
        self.update_effects() # Pri 10
        self.update_bullets() # Pri 11
        # Pri 12 is HUD

        # 4. Cleaning
        self.cleanup()

        self.frame += 1


    def update_enemies(self):
        for enemy in self.enemies:
            enemy.update()


    def update_players(self, keystate):
        for player in self.players:
            player.update(keystate) #TODO: differentiate keystates (multiplayer mode)
            if player.state.x < 8.:
                player.state.x = 8.
            if player.state.x > 384.-8: #TODO
                player.state.x = 384.-8
            if player.state.y < 16.:
                player.state.y = 16.
            if player.state.y > 448.-16: #TODO
                player.state.y = 448.-16

        for bullet in self.players_bullets:
            bullet.update()


    def update_effects(self):
        for effect in self.effects:
            effect.update()


    def update_bullets(self):
        for bullet in self.cancelled_bullets:
            bullet.update()

        for bullet in self.bullets:
            bullet.update()

        for item in self.items:
            item.update()

        for player in self.players:
            if not player.state.touchable:
                continue

            px, py = player.x, player.y
            phalf_size = player.hitbox_half_size
            px1, px2 = px - phalf_size, px + phalf_size
            py1, py2 = py - phalf_size, py + phalf_size

            ghalf_size = player.graze_hitbox_half_size
            gx1, gx2 = px - ghalf_size, px + ghalf_size
            gy1, gy2 = py - ghalf_size, py + ghalf_size

            for bullet in self.bullets:
                half_size = bullet.hitbox_half_size
                bx, by = bullet.x, bullet.y
                bx1, bx2 = bx - half_size, bx + half_size
                by1, by2 = by - half_size, by + half_size

                if not (bx2 < px1 or bx1 > px2
                        or by2 < py1 or by1 > py2):
                    bullet.collide()
                    if player.state.invulnerable_time == 0:
                        player.collide()

                elif not bullet.grazed and not (bx2 < gx1 or bx1 > gx2
                        or by2 < gy1 or by1 > gy2):
                    bullet.grazed = True
                    player.state.graze += 1
                    player.state.score += 500 # found experimentally
                    self.modify_difficulty(+6)
                    self.new_particle((px, py), 0, .8, 192) #TODO: find the real size and range.
                    #TODO: display a static particle during one frame at
                    # 12 pixels of the player, in the axis of the “collision”.

            for item in self.items:
                half_size = item.hitbox_half_size
                bx, by = item.x, item.y
                bx1, bx2 = bx - half_size, bx + half_size
                by1, by2 = by - half_size, by + half_size

                if not (bx2 < px1 or bx1 > px2
                        or by2 < py1 or by1 > py2):
                    item.on_collect(player.state)


    def cleanup(self):
        # Filter out non-visible enemies
        for enemy in tuple(self.enemies):
            if enemy.is_visible(384, 448): #TODO
                enemy._was_visible = True
            elif enemy._was_visible:
                # Filter out-of-screen enemy
                enemy._removed = True
                self.enemies.remove(enemy)

        # Filter out-of-scren bullets
        # TODO: was_visible thing
        self.bullets = [bullet for bullet in self.bullets if bullet.is_visible(384, 448)]
        self.cancelled_bullets = [bullet for bullet in self.cancelled_bullets if bullet.is_visible(384, 448)]
        self.players_bullets = [bullet for bullet in self.players_bullets if bullet.is_visible(384, 448)]

        # Filter out-of-scren items
        items = []
        for item in self.items:
            if item.y < 448:
                items.append(item)
            else:
                self.modify_difficulty(-3)
        self.items = items

        # Disable boss mode if it is dead/it has timeout
        if self.boss and self.boss._removed:
            self.boss = None

