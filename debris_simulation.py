"""
Advanced Debris Simulation with Semi-Rigid and Rigid Bodies
Author: Claude
Description: Simulates debris physics with different material properties
"""

import pygame
import numpy as np
import random
import math
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
GRAVITY = np.array([0, 500])  # Pixels per second squared
AIR_RESISTANCE = 0.99
GROUND_Y = SCREEN_HEIGHT - 50
RESTITUTION = 0.7
FRICTION = 0.8
FPS = 60

class MaterialType(Enum):
    RIGID = "rigid"
    SEMI_RIGID = "semi_rigid"
    SOFT = "soft"

@dataclass
class Material:
    density: float
    elasticity: float
    damping: float
    color: Tuple[int, int, int]
    deformation_threshold: float

# Material definitions
MATERIALS = {
    MaterialType.RIGID: Material(2.5, 0.2, 0.95, (150, 150, 150), 1000),
    MaterialType.SEMI_RIGID: Material(1.8, 0.6, 0.85, (200, 150, 100), 300),
    MaterialType.SOFT: Material(1.0, 0.9, 0.7, (100, 200, 150), 50)
}

class Vector2D:
    """Utility class for 2D vector operations"""
    
    @staticmethod
    def magnitude(vec: np.ndarray) -> float:
        return np.linalg.norm(vec)
    
    @staticmethod
    def normalize(vec: np.ndarray) -> np.ndarray:
        mag = Vector2D.magnitude(vec)
        if mag == 0:
            return vec
        return vec / mag
    
    @staticmethod
    def distance(pos1: np.ndarray, pos2: np.ndarray) -> float:
        return Vector2D.magnitude(pos2 - pos1)

class DebrisParticle:
    """Individual debris particle with physics properties"""
    
    def __init__(self, position: np.ndarray, velocity: np.ndarray, 
                 size: float, material_type: MaterialType):
        self.position = position.astype(float)
        self.velocity = velocity.astype(float)
        self.size = size
        self.mass = (size ** 2) * MATERIALS[material_type].density / 1000
        self.material_type = material_type
        self.material = MATERIALS[material_type]
        
        # Physics properties
        self.angular_velocity = random.uniform(-5, 5)
        self.angle = random.uniform(0, 2 * math.pi)
        self.forces = np.array([0.0, 0.0])
        
        # Deformation properties for semi-rigid bodies
        self.deformation = 0.0
        self.stress = 0.0
        self.original_size = size
        
        # Trail effect
        self.trail = []
        self.max_trail_length = 10
        
        # Collision properties
        self.collision_count = 0
        self.last_collision_time = 0
        
    def apply_force(self, force: np.ndarray):
        """Apply external force to the particle"""
        self.forces += force
    
    def update_deformation(self, collision_force: float):
        """Update deformation based on collision forces"""
        if self.material_type == MaterialType.SEMI_RIGID:
            stress_increment = collision_force / (self.mass * 100)
            self.stress += stress_increment
            
            if self.stress > self.material.deformation_threshold:
                deformation_amount = (self.stress - self.material.deformation_threshold) / 1000
                self.deformation = min(self.deformation + deformation_amount, 0.3)
                self.size = self.original_size * (1 - self.deformation)
            
            # Stress relaxation
            self.stress *= 0.95
    
    def update(self, dt: float, current_time: float):
        """Update particle physics"""
        # Apply gravity
        gravity_force = GRAVITY * self.mass
        self.apply_force(gravity_force)
        
        # Calculate acceleration
        acceleration = self.forces / self.mass
        
        # Update velocity
        self.velocity += acceleration * dt
        self.velocity *= AIR_RESISTANCE  # Air resistance
        
        # Update position
        self.position += self.velocity * dt
        
        # Update angular velocity
        self.angular_velocity *= 0.99  # Angular damping
        self.angle += self.angular_velocity * dt
        
        # Update trail
        self.trail.append(self.position.copy())
        if len(self.trail) > self.max_trail_length:
            self.trail.pop(0)
        
        # Reset forces
        self.forces = np.array([0.0, 0.0])
        
        # Boundary collisions
        self.handle_boundary_collisions(current_time)
    
    def handle_boundary_collisions(self, current_time: float):
        """Handle collisions with screen boundaries"""
        collision_occurred = False
        
        # Ground collision
        if self.position[1] + self.size > GROUND_Y:
            self.position[1] = GROUND_Y - self.size
            
            # Calculate collision force
            collision_force = abs(self.velocity[1]) * self.mass
            
            # Apply material-specific collision response
            if self.material_type == MaterialType.RIGID:
                self.velocity[1] = -self.velocity[1] * self.material.elasticity
                self.velocity[0] *= FRICTION
            else:
                self.velocity[1] = -self.velocity[1] * self.material.elasticity * self.material.damping
                self.velocity[0] *= FRICTION * 0.8
            
            self.update_deformation(collision_force)
            collision_occurred = True
        
        # Wall collisions
        if self.position[0] - self.size < 0:
            self.position[0] = self.size
            self.velocity[0] = -self.velocity[0] * self.material.elasticity
            collision_occurred = True
        elif self.position[0] + self.size > SCREEN_WIDTH:
            self.position[0] = SCREEN_WIDTH - self.size
            self.velocity[0] = -self.velocity[0] * self.material.elasticity
            collision_occurred = True
        
        if collision_occurred:
            self.collision_count += 1
            self.last_collision_time = current_time
    
    def draw(self, screen: pygame.Surface):
        """Render the particle"""
        # Draw trail
        if len(self.trail) > 1:
            for i in range(len(self.trail) - 1):
                alpha = int(255 * (i / len(self.trail)) * 0.5)
                trail_color = (*self.material.color, alpha)
                start_pos = self.trail[i].astype(int)
                end_pos = self.trail[i + 1].astype(int)
                
                if 0 <= start_pos[0] < SCREEN_WIDTH and 0 <= start_pos[1] < SCREEN_HEIGHT:
                    pygame.draw.line(screen, self.material.color[:3], start_pos, end_pos, 2)
        
        # Calculate color based on deformation and stress
        base_color = list(self.material.color)
        if self.material_type == MaterialType.SEMI_RIGID:
            stress_factor = min(self.stress / self.material.deformation_threshold, 1.0)
            base_color[0] = min(255, int(base_color[0] + stress_factor * 100))
        
        # Draw particle
        pos = self.position.astype(int)
        size = int(self.size)
        
        if self.material_type == MaterialType.RIGID:
            # Draw as square for rigid bodies
            points = []
            for i in range(4):
                angle = self.angle + i * math.pi / 2
                x = pos[0] + size * math.cos(angle)
                y = pos[1] + size * math.sin(angle)
                points.append((x, y))
            pygame.draw.polygon(screen, base_color, points)
        else:
            # Draw as circle for semi-rigid and soft bodies
            pygame.draw.circle(screen, base_color, pos, size)
            
            # Draw deformation indicator for semi-rigid
            if self.material_type == MaterialType.SEMI_RIGID and self.deformation > 0:
                deform_size = int(size * (1 + self.deformation))
                pygame.draw.circle(screen, (255, 100, 100), pos, deform_size, 2)
        
        # Draw velocity vector (scaled down)
        if Vector2D.magnitude(self.velocity) > 10:
            vel_end = pos + (self.velocity * 0.1).astype(int)
            pygame.draw.line(screen, (255, 255, 255), pos, vel_end, 2)

class ExplosionSystem:
    """Manages explosion effects and debris generation"""
    
    def __init__(self):
        self.particles: List[DebrisParticle] = []
        self.explosions = []
    
    def create_explosion(self, position: np.ndarray, force: float, 
                        particle_count: int, material_type: MaterialType):
        """Create an explosion at the specified position"""
        for _ in range(particle_count):
            # Random direction
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(force * 0.3, force)
            velocity = np.array([
                math.cos(angle) * speed,
                math.sin(angle) * speed - random.uniform(0, 200)  # Slight upward bias
            ])
            
            # Random offset from explosion center
            offset_distance = random.uniform(0, 30)
            offset = np.array([
                math.cos(angle) * offset_distance,
                math.sin(angle) * offset_distance
            ])
            
            particle_pos = position + offset
            size = random.uniform(3, 15)
            
            particle = DebrisParticle(particle_pos, velocity, size, material_type)
            self.particles.append(particle)
        
        # Add visual explosion effect
        self.explosions.append({
            'position': position.copy(),
            'time': pygame.time.get_ticks(),
            'duration': 500
        })
    
    def update(self, dt: float):
        """Update all particles and effects"""
        current_time = pygame.time.get_ticks()
        
        # Update particles
        self.particles = [p for p in self.particles if self.is_particle_active(p)]
        
        for particle in self.particles:
            particle.update(dt, current_time)
        
        # Update explosions
        self.explosions = [exp for exp in self.explosions 
                          if current_time - exp['time'] < exp['duration']]
    
    def is_particle_active(self, particle: DebrisParticle) -> bool:
        """Check if particle should remain active"""
        # Remove particles that are off-screen and moving away
        if (particle.position[0] < -100 or particle.position[0] > SCREEN_WIDTH + 100 or
            particle.position[1] > SCREEN_HEIGHT + 100):
            if Vector2D.magnitude(particle.velocity) < 50:
                return False
        
        # Remove very slow particles after some time
        if Vector2D.magnitude(particle.velocity) < 10 and particle.collision_count > 5:
            return False
        
        return True
    
    def draw(self, screen: pygame.Surface):
        """Render all effects"""
        current_time = pygame.time.get_ticks()
        
        # Draw explosion effects
        for explosion in self.explosions:
            progress = (current_time - explosion['time']) / explosion['duration']
            if progress < 1.0:
                radius = int(50 * progress)
                alpha = int(255 * (1 - progress))
                pos = explosion['position'].astype(int)
                
                # Create explosion circle effect
                for r in range(0, radius, 5):
                    color_intensity = int(255 * (1 - r / radius) * (1 - progress))
                    color = (min(255, color_intensity + 100), color_intensity, 0)
                    if r < radius:
                        pygame.draw.circle(screen, color, pos, r, 2)
        
        # Draw particles
        for particle in self.particles:
            particle.draw(screen)
    
    def get_particle_count(self) -> int:
        return len(self.particles)

class DebrisSimulation:
    """Main simulation class"""
    
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Advanced Debris Simulation - Semi-Rigid & Rigid Bodies")
        self.clock = pygame.time.Clock()
        
        self.explosion_system = ExplosionSystem()
        self.running = True
        self.paused = False
        
        # UI elements
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        
        # Simulation state
        self.current_material = MaterialType.SEMI_RIGID
        self.explosion_force = 300
        self.particle_count = 20
    
    def handle_events(self):
        """Handle user input"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_c:
                    self.explosion_system.particles.clear()
                elif event.key == pygame.K_1:
                    self.current_material = MaterialType.RIGID
                elif event.key == pygame.K_2:
                    self.current_material = MaterialType.SEMI_RIGID
                elif event.key == pygame.K_3:
                    self.current_material = MaterialType.SOFT
                elif event.key == pygame.K_UP:
                    self.explosion_force = min(1000, self.explosion_force + 50)
                elif event.key == pygame.K_DOWN:
                    self.explosion_force = max(100, self.explosion_force - 50)
                elif event.key == pygame.K_LEFT:
                    self.particle_count = max(5, self.particle_count - 5)
                elif event.key == pygame.K_RIGHT:
                    self.particle_count = min(50, self.particle_count + 5)
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    mouse_pos = np.array(pygame.mouse.get_pos(), dtype=float)
                    self.explosion_system.create_explosion(
                        mouse_pos, self.explosion_force, 
                        self.particle_count, self.current_material
                    )
    
    def draw_ui(self):
        """Draw user interface"""
        # Background for UI
        ui_rect = pygame.Rect(10, 10, 400, 200)
        pygame.draw.rect(self.screen, (0, 0, 0, 128), ui_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), ui_rect, 2)
        
        # Title
        title_text = self.font.render("Advanced Debris Simulation", True, (255, 255, 255))
        self.screen.blit(title_text, (20, 20))
        
        # Instructions
        instructions = [
            "Left Click: Create Explosion",
            "1/2/3: Change Material (Rigid/Semi-Rigid/Soft)",
            "Up/Down: Adjust Force",
            "Left/Right: Adjust Particle Count",
            "Space: Pause/Resume",
            "C: Clear All Particles"
        ]
        
        y_offset = 50
        for instruction in instructions:
            text = self.small_font.render(instruction, True, (200, 200, 200))
            self.screen.blit(text, (20, y_offset))
            y_offset += 20
        
        # Current settings
        settings_y = SCREEN_HEIGHT - 120
        settings_bg = pygame.Rect(10, settings_y, 350, 100)
        pygame.draw.rect(self.screen, (0, 0, 0, 128), settings_bg)
        pygame.draw.rect(self.screen, (255, 255, 255), settings_bg, 2)
        
        settings = [
            f"Material: {self.current_material.value.title()}",
            f"Explosion Force: {self.explosion_force}",
            f"Particle Count: {self.particle_count}",
            f"Active Particles: {self.explosion_system.get_particle_count()}"
        ]
        
        y_offset = settings_y + 10
        for setting in settings:
            color = (100, 255, 100) if "Active" in setting else (255, 255, 255)
            text = self.small_font.render(setting, True, color)
            self.screen.blit(text, (20, y_offset))
            y_offset += 20
        
        # Material color indicator
        material_color = MATERIALS[self.current_material].color
        pygame.draw.circle(self.screen, material_color, (300, settings_y + 25), 15)
        
        # Pause indicator
        if self.paused:
            pause_text = self.font.render("PAUSED", True, (255, 255, 0))
            text_rect = pause_text.get_rect(center=(SCREEN_WIDTH // 2, 50))
            self.screen.blit(pause_text, text_rect)
    
    def draw_ground(self):
        """Draw the ground surface"""
        pygame.draw.rect(self.screen, (101, 67, 33), 
                        (0, GROUND_Y, SCREEN_WIDTH, SCREEN_HEIGHT - GROUND_Y))
        pygame.draw.line(self.screen, (139, 117, 0), 
                        (0, GROUND_Y), (SCREEN_WIDTH, GROUND_Y), 3)
    
    def run(self):
        """Main simulation loop"""
        print("Starting Advanced Debris Simulation...")
        print("Click anywhere to create explosions!")
        
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0  # Delta time in seconds
            
            self.handle_events()
            
            if not self.paused:
                self.explosion_system.update(dt)
            
            # Render
            self.screen.fill((20, 30, 50))  # Dark blue background
            
            self.draw_ground()
            self.explosion_system.draw(self.screen)
            self.draw_ui()
            
            pygame.display.flip()
        
        pygame.quit()
        print("Simulation ended.")

if __name__ == "__main__":
    simulation = DebrisSimulation()
    simulation.run()