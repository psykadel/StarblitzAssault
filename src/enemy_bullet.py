"""Enemy bullet types for the game."""

import math
import random

import pygame

from config.config import SCREEN_HEIGHT, SCREEN_WIDTH

ENEMY_BULLET_SPEED = 5
BULLET_SIZE = (8, 8)


class EnemyBullet(pygame.sprite.Sprite):
    """Basic bullet fired by enemies toward the player."""

    def __init__(self, start_pos: tuple, target_pos: tuple, *groups) -> None:
        super().__init__(*groups)
        self.image = pygame.Surface(BULLET_SIZE, pygame.SRCALPHA)
        pygame.draw.circle(
            self.image, (255, 0, 0), (BULLET_SIZE[0] // 2, BULLET_SIZE[1] // 2), BULLET_SIZE[0] // 2
        )
        self.rect = self.image.get_rect(center=start_pos)
        self.mask = pygame.mask.from_surface(self.image)

        dx = target_pos[0] - start_pos[0]
        dy = target_pos[1] - start_pos[1]
        distance = math.hypot(dx, dy)
        if distance == 0:
            self.velocity = (0, 0)
        else:
            norm_dx = dx / distance
            norm_dy = dy / distance
            self.velocity = (norm_dx * ENEMY_BULLET_SPEED, norm_dy * ENEMY_BULLET_SPEED)

    def update(self) -> None:
        self.rect.x += self.velocity[0]
        self.rect.y += self.velocity[1]
        # Kill the bullet if it goes off screen
        if (
            self.rect.right < 0
            or self.rect.left > SCREEN_WIDTH
            or self.rect.bottom < 0
            or self.rect.top > SCREEN_HEIGHT
        ):
            self.kill()


class BouncingBullet(pygame.sprite.Sprite):
    """Bullet that bounces off screen boundaries."""

    def __init__(self, start_pos: tuple, angle: float, *groups) -> None:
        super().__init__(*groups)

        # Create a larger blue bullet
        self.size = (12, 12)
        self.image = pygame.Surface(self.size, pygame.SRCALPHA)
        pygame.draw.circle(
            self.image,
            (0, 100, 255),  # Blue color
            (self.size[0] // 2, self.size[1] // 2),
            self.size[0] // 2,
        )
        self.rect = self.image.get_rect(center=start_pos)
        self.mask = pygame.mask.from_surface(self.image)

        # Use the provided angle instead of a random one
        speed = ENEMY_BULLET_SPEED * 0.8  # Slightly slower

        # Convert angle to radians and calculate velocity components
        rad_angle = math.radians(angle)
        self.velocity = (-math.cos(rad_angle) * speed, math.sin(rad_angle) * speed)

        # Number of bounces before disappearing
        self.max_bounces = 5
        self.bounce_count = 0

        # Track position as floats for precise movement
        self.pos_x = float(self.rect.x)
        self.pos_y = float(self.rect.y)

    def update(self) -> None:
        # Update position
        self.pos_x += self.velocity[0]
        self.pos_y += self.velocity[1]

        # Update rect from float position
        self.rect.x = round(self.pos_x)
        self.rect.y = round(self.pos_y)

        # Bounce off screen boundaries
        bounced = False

        # Left/right boundaries
        if self.rect.left < 0:
            self.rect.left = 0
            self.pos_x = float(self.rect.x)
            self.velocity = (-self.velocity[0], self.velocity[1])
            bounced = True
        elif self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
            self.pos_x = float(self.rect.x)
            self.velocity = (-self.velocity[0], self.velocity[1])
            bounced = True

        # Top/bottom boundaries
        if self.rect.top < 0:
            self.rect.top = 0
            self.pos_y = float(self.rect.y)
            self.velocity = (self.velocity[0], -self.velocity[1])
            bounced = True
        elif self.rect.bottom > SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT
            self.pos_y = float(self.rect.y)
            self.velocity = (self.velocity[0], -self.velocity[1])
            bounced = True

        # Increment bounce count if bounced
        if bounced:
            self.bounce_count += 1

            # Kill bullet if it's bounced too many times
            if self.bounce_count >= self.max_bounces:
                self.kill()


class SpiralBullet(pygame.sprite.Sprite):
    """Bullet that moves in a spiral pattern."""

    def __init__(self, start_pos: tuple, angle: float, *groups) -> None:
        super().__init__(*groups)

        # Create a green spiral bullet
        self.size = (10, 10)
        self.image = pygame.Surface(self.size, pygame.SRCALPHA)
        pygame.draw.circle(
            self.image,
            (0, 255, 100),  # Green color
            (self.size[0] // 2, self.size[1] // 2),
            self.size[0] // 2,
        )

        # Add a white dot in the center for visual effect
        pygame.draw.circle(
            self.image,
            (255, 255, 255),  # White color
            (self.size[0] // 2, self.size[1] // 2),
            self.size[0] // 6,  # Smaller radius
        )

        self.rect = self.image.get_rect(center=start_pos)
        self.mask = pygame.mask.from_surface(self.image)

        # Spiral movement parameters
        self.angle = angle  # Starting angle in degrees
        self.radius = 0  # Starting radius
        self.radius_growth = 0.5  # How fast the radius grows
        self.rotation_speed = 4  # Degrees per frame
        self.speed = ENEMY_BULLET_SPEED * 0.7  # Forward speed

        # Center position where the spiral originates
        self.center_pos = start_pos
        self.distance_traveled = 0

        # Track position as floats for precise movement
        self.pos_x = float(start_pos[0])
        self.pos_y = float(start_pos[1])

        # Maximum lifetime (frames)
        self.max_lifetime = 180  # 3 seconds at 60 FPS
        self.lifetime = 0

    def update(self) -> None:
        # Increment lifetime
        self.lifetime += 1
        if self.lifetime >= self.max_lifetime:
            self.kill()
            return

        # Move the center position left (overall forward movement)
        self.center_pos = (self.center_pos[0] - self.speed, self.center_pos[1])

        # Increase spiral radius
        self.radius += self.radius_growth

        # Update spiral angle
        self.angle = (self.angle + self.rotation_speed) % 360

        # Calculate new position based on spiral pattern
        rad_angle = math.radians(self.angle)
        offset_x = self.radius * math.cos(rad_angle)
        offset_y = self.radius * math.sin(rad_angle)

        # Update position
        self.pos_x = self.center_pos[0] + offset_x
        self.pos_y = self.center_pos[1] + offset_y

        # Update rect from float position
        self.rect.centerx = round(self.pos_x)
        self.rect.centery = round(self.pos_y)

        # Kill the bullet if it goes off screen
        if (
            self.rect.right < 0
            or self.rect.left > SCREEN_WIDTH
            or self.rect.bottom < 0
            or self.rect.top > SCREEN_HEIGHT
        ):
            self.kill()


class ExplosiveBullet(pygame.sprite.Sprite):
    """Bullet that explodes after a short time or on screen edge contact."""

    def __init__(self, start_pos: tuple, *groups) -> None:
        super().__init__(*groups)

        # Create a yellow-orange explosive bullet
        self.size = (14, 14)
        self.image = pygame.Surface(self.size, pygame.SRCALPHA)

        # Draw a filled circle
        pygame.draw.circle(
            self.image,
            (255, 165, 0),  # Orange color
            (self.size[0] // 2, self.size[1] // 2),
            self.size[0] // 2,
        )

        # Add a yellow border
        pygame.draw.circle(
            self.image,
            (255, 255, 0),  # Yellow color
            (self.size[0] // 2, self.size[1] // 2),
            self.size[0] // 2,
            2,  # Line width
        )

        self.rect = self.image.get_rect(center=start_pos)
        self.mask = pygame.mask.from_surface(self.image)

        # Set straight-line movement to the left with slight randomness
        angle = random.uniform(-30, 30)  # Small random angle variation
        speed = ENEMY_BULLET_SPEED * 0.9

        # Convert angle to radians and calculate velocity
        rad_angle = math.radians(angle)
        self.velocity = (-math.cos(rad_angle) * speed, math.sin(rad_angle) * speed)

        # Track position as floats for precise movement
        self.pos_x = float(start_pos[0])
        self.pos_y = float(start_pos[1])

        # Explosion timer (frames until explosion)
        self.fuse = 90  # 1.5 seconds at 60 FPS
        self.blink_interval = 15  # Frames between blinks
        self.blink_state = False

        # For fragments created on explosion
        self.bullet_group = groups[0] if groups else None

    def update(self) -> None:
        # Update position
        self.pos_x += self.velocity[0]
        self.pos_y += self.velocity[1]

        # Update rect from float position
        self.rect.x = round(self.pos_x)
        self.rect.y = round(self.pos_y)

        # Decrease fuse timer
        self.fuse -= 1

        # Blink as timer runs down
        if self.fuse < 45:  # Start blinking when less than half fuse remains
            if self.fuse % self.blink_interval == 0:
                self.blink_state = not self.blink_state

                if self.blink_state:
                    # Blink to red
                    pygame.draw.circle(
                        self.image,
                        (255, 0, 0),  # Red color
                        (self.size[0] // 2, self.size[1] // 2),
                        self.size[0] // 2,
                    )
                else:
                    # Blink back to orange
                    pygame.draw.circle(
                        self.image,
                        (255, 165, 0),  # Orange color
                        (self.size[0] // 2, self.size[1] // 2),
                        self.size[0] // 2,
                    )

                    # Redraw yellow border
                    pygame.draw.circle(
                        self.image,
                        (255, 255, 0),  # Yellow color
                        (self.size[0] // 2, self.size[1] // 2),
                        self.size[0] // 2,
                        2,  # Line width
                    )

        # Explode if timer reaches zero or hits screen edge
        if (
            self.fuse <= 0
            or self.rect.left < 0
            or self.rect.right > SCREEN_WIDTH
            or self.rect.top < 0
            or self.rect.bottom > SCREEN_HEIGHT
        ):
            self._explode()
            self.kill()

    def _explode(self) -> None:
        """Create explosion fragments."""
        if not self.bullet_group:
            return

        # Create 8 fragments in different directions
        for angle in range(0, 360, 45):
            # Create a small fragment bullet
            fragment = ExplosionFragment(self.rect.center, angle, self.bullet_group)


class ExplosionFragment(pygame.sprite.Sprite):
    """Small fragment created when an explosive bullet explodes."""

    def __init__(self, start_pos: tuple, angle: float, *groups) -> None:
        super().__init__(*groups)

        # Create a small red fragment
        self.size = (6, 6)
        self.image = pygame.Surface(self.size, pygame.SRCALPHA)
        pygame.draw.circle(
            self.image,
            (255, 50, 50),  # Red color
            (self.size[0] // 2, self.size[1] // 2),
            self.size[0] // 2,
        )
        self.rect = self.image.get_rect(center=start_pos)
        self.mask = pygame.mask.from_surface(self.image)

        # Set velocity based on angle
        speed = ENEMY_BULLET_SPEED * 1.2  # Faster than normal bullets
        rad_angle = math.radians(angle)
        self.velocity = (math.cos(rad_angle) * speed, math.sin(rad_angle) * speed)

        # Track position as floats for precise movement
        self.pos_x = float(start_pos[0])
        self.pos_y = float(start_pos[1])

        # Short lifetime
        self.lifetime = 45  # 0.75 seconds at 60 FPS

    def update(self) -> None:
        # Update position
        self.pos_x += self.velocity[0]
        self.pos_y += self.velocity[1]

        # Update rect from float position
        self.rect.x = round(self.pos_x)
        self.rect.y = round(self.pos_y)

        # Decrease lifetime
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()
            return

        # Kill the fragment if it goes off screen
        if (
            self.rect.right < 0
            or self.rect.left > SCREEN_WIDTH
            or self.rect.bottom < 0
            or self.rect.top > SCREEN_HEIGHT
        ):
            self.kill()


class HomingBullet(pygame.sprite.Sprite):
    """Bullet that homes in on the player's position."""

    def __init__(self, start_pos: tuple, player_ref, *groups) -> None:
        super().__init__(*groups)

        # Store player reference for tracking
        self.player_ref = player_ref

        # Create a distinct purple glowing bullet
        self.size = (12, 12)
        self.image = pygame.Surface(self.size, pygame.SRCALPHA)

        # Main purple circle
        pygame.draw.circle(
            self.image,
            (180, 60, 220),  # Purple color
            (self.size[0] // 2, self.size[1] // 2),
            self.size[0] // 2,
        )

        # Inner white circle for glow effect
        pygame.draw.circle(
            self.image,
            (255, 255, 255),  # White color
            (self.size[0] // 2, self.size[1] // 2),
            self.size[0] // 4,  # Quarter size for inner circle
        )

        # Add a light purple outer glow
        pygame.draw.circle(
            self.image,
            (200, 120, 255, 128),  # Semi-transparent light purple
            (self.size[0] // 2, self.size[1] // 2),
            self.size[0] // 2 + 2,  # Slightly larger than main circle
            2,  # Line width
        )

        self.rect = self.image.get_rect(center=start_pos)
        self.mask = pygame.mask.from_surface(self.image)

        # Initial velocity (will be updated to home in on player)
        self.speed = ENEMY_BULLET_SPEED * 0.75  # Slightly slower than normal bullets

        # Initial random direction to create interesting curved paths
        angle = random.uniform(0, 360)
        rad_angle = math.radians(angle)
        self.velocity = (math.cos(rad_angle) * self.speed, math.sin(rad_angle) * self.speed)

        # Position tracking for precision
        self.pos_x = float(start_pos[0])
        self.pos_y = float(start_pos[1])

        # Homing parameters
        self.turn_factor = 0.08  # How quickly it adjusts course (higher = tighter turns)
        self.max_lifetime = 240  # Lifetime in frames (4 seconds at 60 FPS)
        self.lifetime = 0

        # Visual effect parameters
        self.pulse_time = 0
        self.pulse_speed = 0.2

    def update(self) -> None:
        # Update lifetime
        self.lifetime += 1
        if self.lifetime >= self.max_lifetime:
            self.kill()
            return

        # Only track player if they exist
        if self.player_ref and self.player_ref.is_alive:
            # Calculate direction to player
            target_x, target_y = self.player_ref.rect.center
            dx = target_x - self.pos_x
            dy = target_y - self.pos_y

            # Normalize direction
            distance = math.hypot(dx, dy)
            if distance > 0:
                dx /= distance
                dy /= distance

                # Gradually adjust velocity to home in on player
                self.velocity = (
                    self.velocity[0] * (1 - self.turn_factor) + dx * self.speed * self.turn_factor,
                    self.velocity[1] * (1 - self.turn_factor) + dy * self.speed * self.turn_factor,
                )

        # Update position
        self.pos_x += self.velocity[0]
        self.pos_y += self.velocity[1]

        # Update rect from float position
        self.rect.x = round(self.pos_x)
        self.rect.y = round(self.pos_y)

        # Kill the bullet if it goes off screen
        if (
            self.rect.right < 0
            or self.rect.left > SCREEN_WIDTH
            or self.rect.bottom < 0
            or self.rect.top > SCREEN_HEIGHT
        ):
            self.kill()
            return

        # Visual pulsing effect
        self.pulse_time += self.pulse_speed
        pulse_factor = 0.5 + 0.5 * math.sin(self.pulse_time)  # 0.5 to 1.0 range

        # Recreate the image with pulsing glow
        self.image = pygame.Surface(self.size, pygame.SRCALPHA)

        # Main purple circle
        pygame.draw.circle(
            self.image,
            (180, 60, 220),  # Purple color
            (self.size[0] // 2, self.size[1] // 2),
            self.size[0] // 2,
        )

        # Inner white circle for glow effect
        pygame.draw.circle(
            self.image,
            (255, 255, 255),  # White color
            (self.size[0] // 2, self.size[1] // 2),
            self.size[0] // 4 * pulse_factor,  # Pulsing inner circle
        )

        # Add a pulsing light purple outer glow
        glow_alpha = int(128 + 127 * pulse_factor)  # 128-255 range
        pygame.draw.circle(
            self.image,
            (200, 120, 255, glow_alpha),  # Semi-transparent light purple with pulsing alpha
            (self.size[0] // 2, self.size[1] // 2),
            self.size[0] // 2 + 2 * pulse_factor,  # Slightly larger than main circle, pulsing
            2,  # Line width
        )


class WaveBullet(pygame.sprite.Sprite):
    """Bullet that moves in a wave pattern."""

    def __init__(self, start_pos: tuple, direction: int = -1, *groups) -> None:
        """Initialize a wave bullet.

        Args:
            start_pos: Starting position (x, y)
            direction: Direction of travel (-1 for left, 1 for right)
            *groups: Sprite groups to add this bullet to
        """
        super().__init__(*groups)

        # Create a cyan wave bullet
        self.size = (10, 10)
        self.image = pygame.Surface(self.size, pygame.SRCALPHA)

        # Outer cyan circle
        pygame.draw.circle(
            self.image,
            (0, 200, 255),  # Cyan color
            (self.size[0] // 2, self.size[1] // 2),
            self.size[0] // 2,
        )

        # Draw triangular shape inside to indicate direction
        center_x, center_y = self.size[0] // 2, self.size[1] // 2
        pygame.draw.polygon(
            self.image,
            (0, 255, 255),  # Brighter cyan
            [(center_x - 3, center_y), (center_x + 3, center_y - 3), (center_x + 3, center_y + 3)],
        )

        self.rect = self.image.get_rect(center=start_pos)
        self.mask = pygame.mask.from_surface(self.image)

        # Movement parameters
        self.direction = direction  # Travel direction
        self.base_speed = ENEMY_BULLET_SPEED * 1.2  # Slightly faster
        self.wave_amplitude = 40  # Height of wave
        self.wave_frequency = 0.1  # How fast the wave oscillates

        # Position tracking
        self.pos_x = float(start_pos[0])
        self.pos_y = float(start_pos[1])
        self.base_y = float(start_pos[1])  # Original y position
        self.distance_traveled = 0.0  # For wave calculation - float type

        # Maximum lifetime
        self.max_lifetime = 180  # 3 seconds at 60 FPS
        self.lifetime = 0

    def update(self) -> None:
        # Update lifetime
        self.lifetime += 1
        if self.lifetime >= self.max_lifetime:
            self.kill()
            return

        # Move horizontally based on direction
        self.pos_x += self.direction * self.base_speed

        # Update distance traveled for wave calculation
        self.distance_traveled += self.base_speed

        # Calculate wave offset using sine function
        wave_offset = self.wave_amplitude * math.sin(self.distance_traveled * self.wave_frequency)

        # Apply wave offset to y position
        self.pos_y = self.base_y + wave_offset

        # Update rect from float position
        self.rect.x = round(self.pos_x)
        self.rect.y = round(self.pos_y)

        # Kill the bullet if it goes off screen
        if (
            self.rect.right < 0
            or self.rect.left > SCREEN_WIDTH
            or self.rect.bottom < 0
            or self.rect.top > SCREEN_HEIGHT
        ):
            self.kill()
