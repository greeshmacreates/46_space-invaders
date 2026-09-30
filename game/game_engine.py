import pygame
import random
from .player import Player
from .enemy import EnemyGrid
from .bullet import Bullet
from .sounds import Sounds

# Game Engine

WHITE = (255, 255, 255)
GREEN = (0, 200, 0)
RED = (220, 60, 60)
YELLOW = (240, 220, 80)

# Difficulty presets:
#   speed        - how fast the enemy grid marches
#   fire_chance  - chance PER FRAME that the grid fires one shot (60 frames = 1 second)
#   bullet_speed - how fast enemy bullets fall
#   drop         - how many pixels the grid moves down at each screen edge
DIFFICULTIES = {
    "Easy":   {"speed": 1.0, "fire_chance": 0.012, "bullet_speed": 3, "drop": 10},
    "Medium": {"speed": 1.5, "fire_chance": 0.022, "bullet_speed": 4, "drop": 15},
    "Hard":   {"speed": 2.5, "fire_chance": 0.045, "bullet_speed": 6, "drop": 20},
}
DIFFICULTY_KEYS = {
    pygame.K_1: "Easy",
    pygame.K_2: "Medium",
    pygame.K_3: "Hard",
}


class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.sounds = Sounds()
        self.font = pygame.font.SysFont("Arial", 30)
        self.big_font = pygame.font.SysFont("Arial", 64, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 26)

        self.should_quit = False
        self.reset("Medium")

    def reset(self, difficulty):
        """Start a fresh game at the chosen difficulty."""
        settings = DIFFICULTIES[difficulty]
        self.difficulty = difficulty

        self.player = Player(self.width // 2 - 20, self.height - 50, 40, 20)
        self.base_speed = settings["speed"]
        self.drop = settings["drop"]
        self.wave = 1
        self.enemy_grid = EnemyGrid(self.width, speed=self.base_speed, drop_amount=self.drop)

        self.player_bullets = []
        self.enemy_bullets = []
        self._shoot_cooldown = 0
        self.enemy_fire_chance = settings["fire_chance"]
        self.enemy_bullet_speed = settings["bullet_speed"]

        self.score = 0
        self.game_over = False

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if self.game_over:
            if event.key in DIFFICULTY_KEYS:
                self.reset(DIFFICULTY_KEYS[event.key])
            elif event.key in (pygame.K_q, pygame.K_ESCAPE):
                self.should_quit = True
            return

        if event.key == pygame.K_SPACE and self._shoot_cooldown <= 0:
            bullet_x = self.player.center_x() - 2
            self.player_bullets.append(Bullet(bullet_x, self.player.y, direction=-1))
            self._shoot_cooldown = 15
            self.sounds.play_fire()

    def handle_input(self):
        if self.game_over:
            return
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.player.move(-self.player.speed, self.width)
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.player.move(self.player.speed, self.width)

    def _front_line_enemies(self):
        """Lowest alive enemy in each column - only these can shoot."""
        lowest = {}
        for e in self.enemy_grid.alive_enemies():
            col = e.col
            if col not in lowest or e.y > lowest[col].y:
                lowest[col] = e
        return list(lowest.values())

    def _next_wave(self):
        self.wave += 1
        self.enemy_grid = EnemyGrid(
            self.width, speed=self.base_speed + 0.3 * (self.wave - 1), drop_amount=self.drop)
        self.enemy_bullets = []

    def _end_game(self):
        if not self.game_over:
            self.game_over = True
            self.sounds.play_game_over()

    def update(self):
        if self.game_over:
            return

        if self._shoot_cooldown > 0:
            self._shoot_cooldown -= 1

        self.enemy_grid.move()

        # Occasionally one front-line enemy fires back
        shooters = self._front_line_enemies()
        if shooters and random.random() < self.enemy_fire_chance:
            shooter = random.choice(shooters)
            bullet_x = shooter.x + shooter.width // 2
            self.enemy_bullets.append(
                Bullet(bullet_x, shooter.y + shooter.height,
                       speed=self.enemy_bullet_speed, direction=1)
            )

        for bullet in self.player_bullets:
            bullet.move()
        for bullet in self.enemy_bullets:
            bullet.move()

        self.player_bullets = [b for b in self.player_bullets if not b.off_screen(self.height)]
        self.enemy_bullets = [b for b in self.enemy_bullets if not b.off_screen(self.height)]

        # Task 1 fix: never remove from a list while iterating over it.
        # Collect the bullets that hit something, then rebuild the list once.
        # A swept rect is used so a fast bullet can't skip over an enemy
        # between two frames.
        spent_bullets = []
        for bullet in self.player_bullets:
            bullet_area = bullet.swept_rect()
            for enemy in self.enemy_grid.alive_enemies():
                if bullet_area.colliderect(enemy.rect()):
                    enemy.alive = False
                    spent_bullets.append(bullet)
                    self.score += 1
                    self.sounds.play_explosion()
                    break  # one bullet destroys at most one enemy
        if spent_bullets:
            self.player_bullets = [b for b in self.player_bullets if b not in spent_bullets]

        if not self.enemy_grid.alive_enemies():
            self._next_wave()

        player_rect = self.player.rect()
        for bullet in self.enemy_bullets:
            if bullet.swept_rect().colliderect(player_rect):
                self._end_game()
                break

        if self.enemy_grid.reached_bottom(self.player.y):
            self._end_game()

    def render(self, screen):
        pygame.draw.rect(screen, GREEN, self.player.rect())

        for enemy in self.enemy_grid.alive_enemies():
            pygame.draw.rect(screen, WHITE, enemy.rect())

        for bullet in self.player_bullets:
            pygame.draw.rect(screen, WHITE, bullet.rect())
        for bullet in self.enemy_bullets:
            pygame.draw.rect(screen, RED, bullet.rect())

        score_text = self.font.render(f"Score: {self.score}", True, WHITE)
        screen.blit(score_text, (10, 10))

        if self.game_over:
            self._render_game_over(screen)

    def _render_game_over(self, screen):
        # Dim the frozen game behind the overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        cx = self.width // 2
        lines = [
            (self.big_font, "GAME OVER", RED, 200),
            (self.font, f"Final Score: {self.score}", WHITE, 290),
            (self.small_font, "Play again - choose difficulty:", YELLOW, 380),
            (self.small_font, "1 - Easy", WHITE, 425),
            (self.small_font, "2 - Medium", WHITE, 460),
            (self.small_font, "3 - Hard", WHITE, 495),
            (self.small_font, "Q / Esc - Quit", WHITE, 560),
        ]
        for font, text, color, y in lines:
            surf = font.render(text, True, color)
            screen.blit(surf, surf.get_rect(center=(cx, y)))
