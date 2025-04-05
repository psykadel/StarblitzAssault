import pygame
import math

from src.config import SCREEN_WIDTH, SCREEN_HEIGHT

ENEMY_BULLET_SPEED = 5
BULLET_SIZE = (8, 8)


class EnemyBullet(pygame.sprite.Sprite):
    """Bullet fired by an enemy towards the player."""
    def __init__(self, start_pos: tuple, target_pos: tuple, *groups) -> None:
        super().__init__(*groups)
        self.image = pygame.Surface(BULLET_SIZE, pygame.SRCALPHA)
        pygame.draw.circle(
            self.image,
            (255, 0, 0),
            (BULLET_SIZE[0] // 2, BULLET_SIZE[1] // 2),
            BULLET_SIZE[0] // 2
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
        if (self.rect.right < 0 or self.rect.left > SCREEN_WIDTH or
            self.rect.bottom < 0 or self.rect.top > SCREEN_HEIGHT):
            self.kill() 