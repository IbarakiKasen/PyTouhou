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


from math import atan2, cos, sin

from pytouhou.utils.helpers import get_logger

from pytouhou.vm.common import MetaRegistry, instruction

logger = get_logger(__name__)



class ECLRunner(object):
    __metaclass__ = MetaRegistry
    __slots__ = ('_ecl', '_enemy', '_game_state', 'variables', 'sub', 'frame',
                 'instruction_pointer', 'comparison_reg', 'stack')

    def __init__(self, ecl, sub, enemy, game_state):
        # Things not supposed to change
        self._ecl = ecl
        self._enemy = enemy
        self._game_state = game_state

        # Things supposed to change (and be put in the stack)
        self.variables = [0,  0,  0,  0,
                          0., 0., 0., 0.,
                          0,  0,  0,  0]
        self.comparison_reg = 0
        self.sub = sub
        self.frame = 0
        self.instruction_pointer = 0

        self.stack = []


    def run_iteration(self):
        # First, if enemy is dead, return
        if self._enemy._removed:
            return False

        # Then, check for callbacks
        #TODO

        # Now, process script
        while True:
            try:
                frame, instr_type, rank_mask, param_mask, args = self._ecl.subs[self.sub][self.instruction_pointer]
            except IndexError:
                return False

            if frame > self.frame:
                break
            else:
                self.instruction_pointer += 1


            #TODO: skip bad ranks
            if not rank_mask & (0x100 << self._game_state.rank):
                continue


            if frame == self.frame:
                try:
                    callback = self._handlers[instr_type]
                except KeyError:
                    logger.warn('unhandled opcode %d (args: %r)', instr_type, args)
                else:
                    callback(self, *args)

        self.frame += 1
        return True


    def _getval(self, value):
        if -10012 <= value <= -10001:
            return self.variables[int(-10001-value)]
        elif -10025 <= value <= -10013:
            if value == -10013:
                return self._game_state.rank
            elif value == -10014:
                return self._game_state.difficulty
            elif value == -10015:
                return self._enemy.x
            elif value == -10016:
                return self._enemy.y
            elif value == -10017:
                return self._enemy.z
            elif value == -10018:
                player = self._enemy.select_player(self._game_state.players)
                return player.x
            elif value == -10019:
                player = self._enemy.select_player(self._game_state.players)
                return player.y
            elif value == -10021:
                player = self._enemy.select_player(self._game_state.players)
                return self._enemy.get_player_angle(player)
            elif value == -10022:
                return self._enemy.frame
            elif value == -10024:
                return self._enemy.life
            elif value == -10025:
                return self._enemy.select_player(self._game_state.players).character
            raise NotImplementedError(value) #TODO
        else:
            return value


    def _setval(self, variable_id, value):
        if -10012 <= variable_id <= -10001:
            self.variables[int(-10001-variable_id)] = value
        elif -10025 <= variable_id <= -10013:
            if variable_id == -10015:
                self._enemy.x = value
            elif variable_id == -10016:
                self._enemy.y = value
            elif variable_id == -10017:
                self._enemy.z = value
            elif variable_id == -10022:
                self._enemy.frame = value
            elif variable_id == -10024:
                self._enemy.life = value
            else:
                raise IndexError #TODO: proper exception
        else:
            raise IndexError #TODO: proper exception


    @instruction(0)
    def noop(self):
        pass #TODO: Really?


    @instruction(1)
    def destroy(self, arg):
        #TODO: arg?
        self._enemy._removed = True


    @instruction(2)
    def relative_jump(self, frame, instruction_pointer):
        """Jumps to a relative offset in the same subroutine.

        Warning: the relative offset has been translated to an instruction pointer
        by the ECL parsing code (see pytouhou.formats.ecl).
        """
        self.frame, self.instruction_pointer = frame, instruction_pointer


    @instruction(3)
    def relative_jump_ex(self, frame, instruction_pointer, variable_id):
        """If the given variable is non-zero, decrease it by 1 and jump to a
        relative offset in the same subroutine.

        Warning: the relative offset has been translated to an instruction pointer
        by the ECL parsing code (see pytouhou.formats.ecl).
        """
        counter_value = self._getval(variable_id)
        if counter_value:
            self._setval(variable_id, counter_value - 1)
            self.frame, self.instruction_pointer = frame, instruction_pointer


    @instruction(4)
    @instruction(5)
    def set_variable(self, variable_id, value):
        self._setval(variable_id, self._getval(value))


    @instruction(6)
    def set_random_int(self, variable_id, maxval):
        """Set the specified variable to a random int in the [0, maxval) range.
        """
        self._setval(variable_id, int(self._getval(maxval) * self._game_state.prng.rand_double()))


    @instruction(8)
    def set_random_float(self, variable_id, maxval):
        """Set the specified variable to a random float in [0, maxval) range.
        """
        self._setval(variable_id, self._getval(maxval) * self._game_state.prng.rand_double())


    @instruction(9)
    def set_random_float2(self, variable_id, minval, amp):
        self._setval(variable_id, self._getval(minval) + self._getval(amp) * self._game_state.prng.rand_double())


    @instruction(13)
    def set_random_int2(self, variable_id, minval, amp):
        self._setval(variable_id, int(self._getval(minval)) + int(self._getval(amp)) * self._game_state.prng.rand_double())


    @instruction(14)
    @instruction(21)
    def substract(self, variable_id, a, b):
        #TODO: 14 takes only ints and 21 only floats.
        # The original engine dereferences the variables in the type it waits for, so this isn't exactly the correct implementation, but the data don't contain such case.
        self._setval(variable_id, self._getval(a) - self._getval(b))


    @instruction(15)
    def multiply_int(self, variable_id, a, b):
        #TODO: takes only ints.
        self._setval(variable_id, self._getval(a) * self._getval(b))


    @instruction(16)
    def divide_int(self, variable_id, a, b):
        #TODO: takes only ints.
        self._setval(variable_id, self._getval(a) // self._getval(b))


    @instruction(17)
    def modulo(self, variable_id, a, b):
        self._setval(variable_id, self._getval(a) % self._getval(b))


    @instruction(20)
    def add_float(self, variable_id, a, b):
        #TODO: takes only floats.
        self._setval(variable_id, self._getval(a) + self._getval(b))


    @instruction(23)
    def divide_float(self, variable_id, a, b):
        #TODO: takes only floats.
        self._setval(variable_id, self._getval(a) / self._getval(b))


    @instruction(27)
    @instruction(28)
    def compare(self, a, b):
        #TODO: 27 takes only ints and 28 only floats.
        a, b = self._getval(a), self._getval(b)
        if a < b:
            self.comparison_reg = -1
        elif a == b:
            self.comparison_reg = 0
        else:
            self.comparison_reg = 1


    @instruction(29)
    def relative_jump_if_lower_than(self, frame, instruction_pointer):
        if self.comparison_reg == -1:
            self.relative_jump(frame, instruction_pointer)


    @instruction(30)
    def relative_jump_if_lower_or_equal(self, frame, instruction_pointer):
        if self.comparison_reg != 1:
            self.relative_jump(frame, instruction_pointer)


    @instruction(31)
    def relative_jump_if_equal(self, frame, instruction_pointer):
        if self.comparison_reg == 0:
            self.relative_jump(frame, instruction_pointer)


    @instruction(32)
    def relative_jump_if_greater_than(self, frame, instruction_pointer):
        if self.comparison_reg == 1:
            self.relative_jump(frame, instruction_pointer)


    @instruction(33)
    def relative_jump_if_greater_or_equal(self, frame, instruction_pointer):
        if self.comparison_reg != -1:
            self.relative_jump(frame, instruction_pointer)


    @instruction(34)
    def relative_jump_if_not_equal(self, frame, instruction_pointer):
        if self.comparison_reg != 0:
            self.relative_jump(frame, instruction_pointer)


    @instruction(35)
    def call(self, sub, param1, param2):
        self.stack.append((self.sub, self.frame, self.instruction_pointer,
                           self.variables, self.comparison_reg))
        self.sub = sub
        self.frame = 0
        self.instruction_pointer = 0
        self.variables = [param1, 0,  0,  0,
                          param2, 0., 0., 0.,
                          0,      0,  0,  0]


    @instruction(36)
    def ret(self):
        self.sub, self.frame, self.instruction_pointer, self.variables, self.comparison_reg = self.stack.pop()


    @instruction(39)
    def call_if_equal(self, sub, param1, param2, a, b):
        if self._getval(a) == self._getval(b):
            self.call(sub, param1, param2)


    @instruction(43)
    def set_pos(self, x, y, z):
        self._enemy.set_pos(x, y, z)


    @instruction(45)
    def set_angle_speed(self, angle, speed):
        self._enemy.angle, self._enemy.speed = angle, speed


    @instruction(46)
    def set_rotation_speed(self, speed):
        self._enemy.rotation_speed = speed


    @instruction(47)
    def set_speed(self, speed):
        self._enemy.speed = speed


    @instruction(48)
    def set_acceleration(self, acceleration):
        self._enemy.acceleration = acceleration


    @instruction(49)
    def set_random_angle(self, min_angle, max_angle):
        angle = self._game_state.prng.rand_double() * (max_angle - min_angle) + min_angle
        self._enemy.angle = angle


    @instruction(50)
    def set_random_angle_ex(self, min_angle, max_angle):
        if self._enemy.screen_box:
            minx, miny, maxx, maxy = self._enemy.screen_box
        else:
            minx, miny, maxx, maxy = (0., 0., 0., 0.)

        angle = self._game_state.prng.rand_double() * (max_angle - min_angle) + min_angle
        sa, ca = sin(angle), cos(angle)

        distx = min(96.0, (maxx - minx) / 2.)
        disty = min(96.0, (maxy - miny) / 2.)

        if self._enemy.x > maxx - 96.0:
            ca = -abs(ca)
        elif self._enemy.x < minx + 96.0:
            ca = abs(ca)

        if self._enemy.y > maxy - 48.0:
            sa = -abs(sa)
        elif self._enemy.y < miny + 48.0:
            sa = abs(sa)
        self._enemy.angle = atan2(sa, ca)


    @instruction(51)
    def target_player(self, unknown, speed):
        #TODO: unknown
        self._enemy.speed = speed
        self._enemy.angle = self._enemy.get_player_angle(self._enemy.select_player(self._game_state.players))


    @instruction(57)
    def move_to(self, duration, x, y, z):
        self._enemy.move_to(duration, x, y, z, lambda x: 2. * x - x ** 2)


    @instruction(59)
    def move_to2(self, duration, x, y, z):
        #TODO: not accurate
        self._enemy.move_to(duration, x, y, z, lambda x: 1.0014 * x ** 2 - 0.0012 * x)


    @instruction(61)
    def stop_in(self, duration):
        self._enemy.stop_in(duration)


    @instruction(65)
    def set_screen_box(self, xmin, ymin, xmax, ymax):
        self._enemy.screen_box = xmin, ymin, xmax, ymax


    @instruction(66)
    def clear_screen_box(self):
        self._enemy.screen_box = None


    @instruction(67)
    def set_bullet_attributes1(self, bullet_anim, launch_anim, bullets_per_shot,
                              number_of_shots, speed, unknown, launch_angle,
                              angle, flags):
        self._enemy.set_bullet_attributes(1, bullet_anim, launch_anim,
                                           bullets_per_shot, number_of_shots,
                                           speed, unknown, launch_angle, angle,
                                           flags)


    @instruction(77)
    def set_bullet_interval(self, value):
        self._enemy.bullet_launch_interval = value


    @instruction(78)
    def set_delay_attack(self):
        self._enemy.delay_attack = True


    @instruction(79)
    def set_no_delay_attack(self):
        self._enemy.delay_attack = False


    @instruction(81)
    def set_bullet_launch_offset(self, x, y, z):
        self._enemy.bullet_launch_offset = (x, y)


    @instruction(97)
    def set_anim(self, sprite_index):
        self._enemy.set_anim(sprite_index)


    @instruction(98)
    def set_multiple_anims(self, default, end_left, end_right, left, right):
        self._enemy.movement_dependant_sprites = end_left, end_right, left, right
        self._enemy.set_anim(default)


    @instruction(100)
    def set_death_anim(self, sprite_index):
        self._enemy.death_anim = sprite_index % 256 #TODO


    @instruction(101)
    def set_boss_mode(self, unknown):
        #TODO: unknown
        self._game_state.boss = self._enemy


    @instruction(103)
    def set_hitbox(self, width, height, depth):
        self._enemy.hitbox = (width, height)


    @instruction(105)
    def set_damageable(self, vulnerable):
        self._enemy.damageable = bool(vulnerable & 1)


    @instruction(108)
    def set_death_callback(self, sub):
        self._enemy.death_callback = sub


    @instruction(109)
    def memory_write(self, value, index):
        #TODO
        #XXX: this is a hack to display bosses although we don't handle MSG :)
        if index == 0:
            self.sub = value
            self.frame = 0
            self.instruction_pointer = 0


    @instruction(111)
    def set_life(self, value):
        self._enemy.life = value


    @instruction(112)
    def set_ellapsed_time(self, value):
        """Sets the enemy's frame counter.
        This is used for timeouts, where the framecounter is compared to the
        timeout value (what's displayed is (enemy.timeout - enemy.frame) // 60).
        """
        self._enemy.frame = value


    @instruction(113)
    def set_low_life_trigger(self, value):
        self._enemy.low_life_trigger = value


    @instruction(114)
    def set_low_life_callback(self, sub):
        self._enemy.low_life_callback = sub


    @instruction(115)
    def set_timeout(self, timeout):
        self._enemy.timeout = timeout


    @instruction(116)
    def set_timeout_callback(self, sub):
        self._enemy.timeout_callback = sub


    @instruction(117)
    def set_touchable(self, value):
        """Defines whether the enemy is “touchable”.
        Bullets only collide with an enemy if it is “touchable”.
        Likewise, ReimuA's homing attacks only target “touchable” enemies.
        """
        self._enemy.touchable = bool(value)


    @instruction(126)
    def set_remaining_lives(self, lives):
        self._enemy.remaining_lives = lives
