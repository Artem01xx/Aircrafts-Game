try:
    import framework32 as framework
except ImportError:
    import framework64 as framework

import math


# -------------------------------------------------------
# Game parameters
# -------------------------------------------------------

class Params:
    class Ship:
        LINEAR_SPEED = 0.5
        ANGULAR_SPEED = 0.5

    class Aircraft:
        LINEAR_SPEED = 2.0
        ANGULAR_SPEED = 2.5
        AIRCRAFT_FLY_TIME = 10.0
        MAX_AIRCRAFT = 5
        AIRCRAFT_CAN_FLY_AGAIN = 5.0
        AIRCRAFT_COUNT = 0
        FLY_AROUND_TARGET = 10


# -------------------------------------------------------
# Basic Vector2 class
# -------------------------------------------------------

class Vector2:

    def __init__(self, *args):
        if not args:
            self.x = self.y = 0.0
        elif len(args) == 1:
            self.x, self.y = args[0].x, args[0].y
        else:
            self.x, self.y = args

    def __add__(self, other):
        return Vector2(self.x + other.x, self.y + other.y)

    def __mul__(self, coef):
        return Vector2(self.x * coef, self.y * coef)

    def __sub__(self, other):
        return Vector2(self.x - other.x, self.y - other.y)

    def magnitude(self):
        return math.hypot(self.x, self.y)

    def normalize(self):
        magnitude = self.magnitude()
        if magnitude != 0:
            self.x /= magnitude
            self.y /= magnitude


# -------------------------------------------------------
# Simple ship logic
# -------------------------------------------------------

class Ship:
    def __init__(self):
        self._model = None
        self.position = None
        self._angle = 0.0
        self._input = {
            framework.Keys.FORWARD: False, framework.Keys.BACKWARD: False, framework.Keys.LEFT: False,
            framework.Keys.RIGHT: False
        }

    def init(self):
        assert not self._model
        self._model = framework.createShipModel()
        self.position = Vector2()
        self._angle = 0.0

    def deinit(self):
        assert self._model
        framework.destroyModel(self._model)
        self._model = None

    def update(self, dt):
        linearSpeed, angularSpeed = 0.0, 0.0

        if self._input[framework.Keys.FORWARD]:
            linearSpeed = Params.Ship.LINEAR_SPEED
        elif self._input[framework.Keys.BACKWARD]:
            linearSpeed = -Params.Ship.LINEAR_SPEED

        if self._input[framework.Keys.LEFT] and linearSpeed != 0.0:
            angularSpeed = Params.Ship.ANGULAR_SPEED
        elif self._input[framework.Keys.RIGHT] and linearSpeed != 0.0:
            angularSpeed = -Params.Ship.ANGULAR_SPEED

        self._angle = self._angle + angularSpeed * dt
        self.position = (self.position + Vector2(math.cos(self._angle), math.sin(self._angle)) * linearSpeed * dt)
        framework.placeModel(self._model, self.position.x, self.position.y, self._angle)

    def key_pressed(self, key):
        self._input[key] = True

    def key_released(self, key):
        self._input[key] = False

    def mouse_clicked(self, x, y, is_left_button):
        if not is_left_button:
            framework.placeGoalModel(x, y)


# -------------------------------------------------------
# Simple aircraft logic
# -------------------------------------------------------

class Aircraft:
    def __init__(self, position, angle):
        self._model = None
        self.position = Vector2(position.x, position.y)
        self._angle = angle
        self.target = None
        self.time_since_takeoff = 0.0
        self.is_landed = True
        self.time_since_landing = None
        self.refuel_time = 5.0
        self.flight_phase = "to_target"
        self.orbit_start_time = 0.0
        self.return_to_base_start_time = 0.0
        self.should_orbit_around_target = False
        self.linear_speed = 2.0

    def takeoff(self):
        if self.is_landed:
            self._model = framework.createAircraftModel()
            self.time_since_takeoff = 0.0
            self.is_landed = False
            self.time_since_landing = None

    def landed(self):
        if not self.is_landed and self._model:
            framework.destroyModel(self._model)
            self._model = None
            self.is_landed = True
            self.time_since_landing = 0.0

    def refuel(self, dt):
        if not self.is_landed or self.time_since_takeoff is None:
            return False
        self.time_since_landing += dt
        if self.time_since_landing >= self.refuel_time:
            Params.Aircraft.AIRCRAFT_COUNT -= 1
            return True
        return False

    def update(self, dt, ship_position_x, ship_position_y):
        if not self.is_landed:
            if self.flight_phase == "to_target":
                self.time_since_takeoff += dt
                if self.time_since_takeoff > Params.Aircraft.AIRCRAFT_FLY_TIME:
                    self.flight_phase = "return_to_base"
                else:
                    direction = Vector2(self.target - self.position)
                    distance = direction.magnitude()
                    direction.normalize()
                    interpolation_factor = min(1.0, self.time_since_takeoff / Params.Aircraft.AIRCRAFT_FLY_TIME)
                    movement = direction * Params.Aircraft.LINEAR_SPEED * dt * interpolation_factor
                    self.position += movement
                    self._angle = math.atan2(direction.y, direction.x)

                    if self._model:
                        framework.placeModel(self._model, self.position.x, self.position.y, self._angle)
                    if distance <= 0.1:
                        if self.should_orbit_around_target:
                            self.flight_phase = "orbit_around_target"
                            self.orbit_start_time = 0.
                        else:
                            self.flight_phase = "return_to_base"
                            self.return_to_base_start_time = 0

            elif self.flight_phase == "orbit_around_target":
                if not self.should_orbit_around_target:
                    self.flight_phase = "return_to_base"
                    self.return_to_base_start_time = 0.0
                else:
                    self.orbit_start_time += dt
                    orbit_radius = 0.7
                    orbit_speed = 0.8
                    orbit_angle = self.orbit_start_time * orbit_speed
                    interpolation_factor = min(1.0, self.orbit_start_time / 50.0)

                    relative_target_position = Vector2(math.cos(orbit_angle), math.sin(orbit_angle)) * orbit_radius
                    target_position = self.target + relative_target_position

                    direction = Vector2(target_position - self.position)
                    direction.normalize()

                    angle_to_center = math.atan2(direction.y, direction.x)
                    self.position = self.position + (target_position - self.position) * interpolation_factor

                    if self._model:
                        framework.placeModel(self._model, self.position.x, self.position.y, angle_to_center)

                    if self.orbit_start_time >= Params.Aircraft.FLY_AROUND_TARGET:
                        self.flight_phase = "return_to_base"
                        self.return_to_base_start_time = 0.0

            elif self.flight_phase == "return_to_base":
                self.return_to_base_start_time += dt
                base_position = Vector2(ship_position_x, ship_position_y)
                direction_to_base = Vector2(base_position - self.position)
                distance_to_base = direction_to_base.magnitude()
                direction_to_base.normalize()

                target_angle = math.atan2(direction_to_base.y, direction_to_base.x)
                time_to_rotate = 5.0
                rotation_progress = min(1.0, self.return_to_base_start_time / time_to_rotate)
                self._angle = self._angle + (target_angle - self._angle) * rotation_progress

                interpolation_factor = min(1.0, self.return_to_base_start_time / Params.Aircraft.AIRCRAFT_FLY_TIME)
                movement_to_base = direction_to_base * Params.Aircraft.LINEAR_SPEED * dt * interpolation_factor
                self.linear_speed = Params.Aircraft.LINEAR_SPEED * (1.0 - interpolation_factor)
                self.position += movement_to_base

                if self._model:
                    framework.placeModel(self._model, self.position.x, self.position.y, self._angle)
                orbit_transition_distance = 0.1
                if distance_to_base <= orbit_transition_distance:
                    self.flight_phase = "landed"
                    self.landed()

        else:
            if self.refuel(dt):
                self.takeoff()
            if self._model:
                framework.destroyModel(self._model)
                self._model = None


# -------------------------------------------------------
# Game public interface
# -------------------------------------------------------

class Game:

    def __init__(self):
        self._ship = Ship()
        self.aircraft_list = []

    def init(self):
        self._ship.init()

    def deinit(self):
        self._ship.deinit()

    def update(self, dt):
        self._ship.update(dt)
        for aircraft in self.aircraft_list:
            aircraft.update(dt, self._ship.position.x, self._ship.position.y)

    def keyPressed(self, key):
        self._ship.key_pressed(key)

    def keyReleased(self, key):
        self._ship.key_released(key)

    def mouseClicked(self, x, y, is_left_button):
        self._ship.mouse_clicked(x, y, is_left_button)
        aircraft = Aircraft(self._ship.position, 0.0)
        orbiting_aircraft = any(aircraft.flight_phase == "orbit_around_target" for aircraft in self.aircraft_list)
        if is_left_button:
            if Params.Aircraft.AIRCRAFT_COUNT < Params.Aircraft.MAX_AIRCRAFT:
                aircraft.target = Vector2(x, y)
                aircraft.takeoff()
                Params.Aircraft.AIRCRAFT_COUNT += 1
                self.aircraft_list.append(aircraft)
        else:
            for aircraft in self.aircraft_list:
                aircraft.should_orbit_around_target = True
                aircraft.target = Vector2(x, y)
                if orbiting_aircraft:
                    aircraft.flight_phase = "to_target"


# -------------------------------------------------------
# Finally we can run our game!
# -------------------------------------------------------
framework.runGame(Game())
