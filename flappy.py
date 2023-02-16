import pygame
import neat
import visualize
import time
import os
import random
import numpy as np

pygame.font.init()

WIDTH = 500
HEIGHT = 800

FPS = 30

PIPE_IMG = pygame.transform.scale2x(pygame.image.load('assets/sprites/pipe-green.png'))
BASE_IMG = pygame.transform.scale2x(pygame.image.load('assets/sprites/base.png'))
BG_IMG = pygame.transform.scale2x(pygame.image.load('assets/sprites/background-day.png'))

STAT_FONT = pygame.font.Font('assets/04B_19__.TTF', 60)
STAT2_FONT = pygame.font.Font('assets/04B_19__.TTF', 30)


GEN = 1

_circle_cache = {}
def _circlepoints(r):
    r = int(round(r))
    if r in _circle_cache:
        return _circle_cache[r]
    x, y, e = r, 0, 1 - r
    _circle_cache[r] = points = []
    while x >= y:
        points.append((x, y))
        y += 1
        if e < 0:
            e += 2 * y - 1
        else:
            x -= 1
            e += 2 * (y - x) - 1
    points += [(y, x) for x, y in points if x > y]
    points += [(-x, y) for x, y in points if x]
    points += [(x, -y) for x, y in points if y]
    points.sort()
    return points

def render(text, font, gfcolor=(255, 255, 255), ocolor=(0, 0, 0), opx=2):
    textsurface = font.render(text, True, gfcolor).convert_alpha()
    w = textsurface.get_width() + 2 * opx
    h = font.get_height()

    osurf = pygame.Surface((w, h + 2 * opx)).convert_alpha()
    osurf.fill((0, 0, 0, 0))

    surf = osurf.copy()

    osurf.blit(font.render(text, True, ocolor).convert_alpha(), (0, 0))

    for dx, dy in _circlepoints(opx):
        surf.blit(osurf, (dx + opx, dy + opx))

    surf.blit(textsurface, (opx, opx))
    return surf

class Bird:
    BIRD_IMGS = np.array([[pygame.transform.scale2x(pygame.image.load('assets/sprites/yellowbird-upflap.png')),
                           pygame.transform.scale2x(pygame.image.load('assets/sprites/yellowbird-midflap.png')),
                           pygame.transform.scale2x(pygame.image.load('assets/sprites/yellowbird-downflap.png'))],
                          [pygame.transform.scale2x(pygame.image.load('assets/sprites/bluebird-upflap.png')),
                           pygame.transform.scale2x(pygame.image.load('assets/sprites/bluebird-midflap.png')),
                           pygame.transform.scale2x(pygame.image.load('assets/sprites/bluebird-downflap.png'))],
                          [pygame.transform.scale2x(pygame.image.load('assets/sprites/redbird-upflap.png')),
                           pygame.transform.scale2x(pygame.image.load('assets/sprites/redbird-midflap.png')),
                           pygame.transform.scale2x(pygame.image.load('assets/sprites/redbird-downflap.png'))]])
    MAX_ROTATION = 25
    ROT_VEL = 20
    ANIMATION_TIME = 5

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.tilt = 0
        self.tick_count = 0  # frame since last jump
        self.vel = 0
        self.height = self.y
        self.img_count = 0
        self.rnd = random.randint(0, 2)
        self.img = self.BIRD_IMGS[self.rnd][0]
        self.d = 0

    def jump(self):
        self.vel = -10.5
        self.tick_count = 0
        self.height = self.y

    def move(self):
        self.tick_count += 1
        self.d = self.vel * self.tick_count + 1.5 * self.tick_count ** 2
        if self.d >= 16:
            self.d = 16
        # if d < 0:
        #   d -= 2
        self.y = self.y + self.d
        if self.d < 0:
            self.tilt += self.ROT_VEL
            if self.tilt > self.MAX_ROTATION:
                self.tilt = self.MAX_ROTATION
        else:
            self.tilt -= self.ROT_VEL
            if self.tilt < -self.MAX_ROTATION:
                self.tilt = -self.MAX_ROTATION

    def draw(self, win):
        self.img_count += 1

        if self.img_count < self.ANIMATION_TIME:
            self.img = self.BIRD_IMGS[self.rnd][0]
        elif self.img_count < self.ANIMATION_TIME * 2:
            self.img = self.BIRD_IMGS[self.rnd][1]
        elif self.img_count < self.ANIMATION_TIME * 3:
            self.img = self.BIRD_IMGS[self.rnd][2]
        elif self.img_count < self.ANIMATION_TIME * 4:
            self.img = self.BIRD_IMGS[self.rnd][1]
        elif self.img_count < self.ANIMATION_TIME * 4 + 1:
            self.img = self.BIRD_IMGS[self.rnd][0]
            self.img_count = 0

        if self.tilt <= -80:
            self.img = self.BIRD_IMGS[self.rnd][1]
            self.img_count = self.ANIMATION_TIME * 2

        rotated_image = pygame.transform.rotate(self.img, self.tilt)
        new_rect = rotated_image.get_rect(center=self.img.get_rect(topleft=(self.x, self.y)).center)
        win.blit(rotated_image, new_rect.topleft)

    def get_mask(self):
        return pygame.mask.from_surface(self.img)


class Pipe:
    def __init__(self, x, score):
        self.gap = random.randint(160, 210)
        self.x = x
        self.height = 0
        self.top = 0
        self.bottom = 0
        self.PIPE_TOP = pygame.transform.flip(PIPE_IMG, False, True)
        self.PIPE_BOTTOM = PIPE_IMG
        self.vel = 5+0.25*score
        if self.vel > 9.5:
            self.vel = 9.5

        self.passed = False
        self.set_height()

    def set_height(self):
        self.height = random.randrange(50, 450)
        self.top = self.height - self.PIPE_TOP.get_height()
        self.bottom = self.height + self.gap

    def move(self):
        self.x -= self.vel

    def draw(self, win):
        win.blit(self.PIPE_TOP, (self.x, self.top))
        win.blit(self.PIPE_BOTTOM, (self.x, self.bottom))

    def collide(self, bird):
        bird_mask = bird.get_mask()
        top_mask = pygame.mask.from_surface(self.PIPE_TOP)
        bottom_mask = pygame.mask.from_surface(self.PIPE_BOTTOM)

        top_offset = (self.x - bird.x, self.top - round(bird.y))
        bottom_offset = (self.x - bird.x, self.bottom - round(bird.y))

        t_point = bird_mask.overlap(top_mask, top_offset)
        b_point = bird_mask.overlap(bottom_mask, bottom_offset)

        if t_point or b_point:
            return True
        return False


class Base:
    WIDTH = BASE_IMG.get_width()
    IMG = BASE_IMG

    def __init__(self, y, score):
        self.y = y
        self.x1 = 0
        self.x2 = self.WIDTH
        self.vel = 5 + 0.25 * score
        if self.vel > 9.5:
            self.vel = 9.5

    def move(self):
        self.x1 -= self.vel
        self.x2 -= self.vel

        if self.x1 + self.WIDTH < 0:
            self.x1 = self.x2 + self.WIDTH
        if self.x2 + self.WIDTH < 0:
            self.x2 = self.x1 + self.WIDTH

    def draw(self, win):
        win.blit(self.IMG, (self.x1, self.y))
        win.blit(self.IMG, (self.x2, self.y))


def draw_window(win, birds, pipes, base, score, fitness):
    win.blit(BG_IMG, (0, 0))
    for pipe in pipes:
        pipe.draw(win)

    base.draw(win)
    for bird in birds:
        bird.draw(win)

    shadow = STAT_FONT.render("{0:0=2d}".format(score), 1, (0, 0, 0))
    shadow_rect = shadow.get_rect(center=(WIDTH/2+3, 63))
    win.blit(shadow, shadow_rect)
    text = render("{0:0=2d}".format(score), STAT_FONT)
    text_rect=text.get_rect(center=(WIDTH/2, 60))
    win.blit(text, text_rect)

    shadow3 = STAT2_FONT.render("Fitness : "+"{0:.1f}".format(fitness), 1, (0, 0, 0))
    win.blit(shadow3, (WIDTH-shadow3.get_width()-5+1, HEIGHT-shadow3.get_height()-5+1.5))
    text3 = render("Fitness : "+"{0:.1f}".format(fitness), STAT2_FONT)
    win.blit(text3, (WIDTH-text3.get_width()-5, HEIGHT-text3.get_height()-5))

    shadow2 = STAT2_FONT.render("{0:0=2d}".format(len(birds))+"/50 Flappies", 1, (0, 0, 0))
    win.blit(shadow2, (WIDTH-shadow2.get_width()-5+1, HEIGHT-shadow3.get_height()-shadow2.get_height()-5-3-5))
    text2 = render("{0:0=2d}".format(len(birds))+"/50 Flappies", STAT2_FONT)
    win.blit(text2, (WIDTH-text2.get_width()-5, HEIGHT-text3.get_height()-text2.get_height()-5-5))

    shadow4 = STAT2_FONT.render("[GEN "+str(GEN)+"]".format(fitness), 1, (0, 0, 0))
    win.blit(shadow4, (WIDTH-shadow4.get_width()-5+1, HEIGHT-shadow4.get_height()-shadow3.get_height()-shadow2.get_height()-5-6.5-5-3))
    text4 = render("[GEN "+str(GEN)+"]", STAT2_FONT)
    win.blit(text4, (WIDTH-text4.get_width()-5, HEIGHT-text4.get_height()-text3.get_height()-text2.get_height()-5-5-3))

    pygame.display.update()

def main(genomes, config):
    nets = []
    ge = []
    birds = []

    for _, g in genomes:
        net = neat.nn.FeedForwardNetwork.create(g, config)
        nets.append(net)
        birds.append(Bird(230, 350))
        g.fitness = 0
        ge.append(g)

    base = Base(730, 0)
    pipes = [Pipe(600, 0)]
    win = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    score = 0

    RUN = True
    while RUN and len(birds) > 0:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                RUN = False
                pygame.quit()
                quit()

        pipe_ind = 0
        if len(birds) > 0:
            if len(pipes) > 1 and birds[0].x > pipes[0].x + pipes[0].PIPE_TOP.get_width():
                pipe_ind = 1

        for x, bird in enumerate(birds):
            bird.move()
            ge[x].fitness += 0.1

            output = nets[x].activate((pipes[pipe_ind].x-bird.x, abs(bird.y - pipes[pipe_ind].height), abs(bird.y - pipes[pipe_ind].bottom), pipes[pipe_ind].vel, bird.tilt, bird.d))

            if output[0] > 0.5:
                bird.jump()

        # bird.move()
        add_pipe = False
        rem = []
        for pipe in pipes:
            for x, bird in enumerate(birds):
                if pipe.collide(bird):
                    ge[x].fitness -= 1
                    birds.pop(x)
                    nets.pop(x)
                    ge.pop(x)
                if bird.y + bird.img.get_height() >= 730 or bird.y < 0:
                    ge[x].fitness -= 1
                    birds.pop(x)
                    nets.pop(x)
                    ge.pop(x)
                if not pipe.passed and pipe.x < bird.x:
                    pipe.passed = True
                    add_pipe = True

            if pipe.x + pipe.PIPE_TOP.get_width() < 0:
                rem.append(pipe)

            pipe.move()

        if add_pipe:
            score += 1
            for g in ge:
                g.fitness += 5
            pipes.append(Pipe(600, score))
            base = Base(730, score)

        for r in rem:
            pipes.remove(r)

        base.move()

        f = 0
        if len(ge)>0:
            f = ge[0].fitness

        draw_window(win, birds, pipes, base, score, f)
    global GEN
    GEN += 1


def run(config_path):
    config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction, neat.DefaultSpeciesSet,
                                neat.DefaultStagnation, config_path)
    p = neat.Population(config)
    p.add_reporter(neat.StdOutReporter(True))
    stat = neat.StatisticsReporter()
    p.add_reporter(stat)

    winner = p.run(main, 50)
    print('\nBest genome:\n{!s}'.format(winner))

    # output = nets[x].activate((pipes[pipe_ind].x - bird.x, abs(bird.y - pipes[pipe_ind].height),abs(bird.y - pipes[pipe_ind].bottom), bird.tilt, bird.d))
    node_names = {-1: 'x-distance', -2: 'top y-distance', -3: 'bottom y-distance', -4: 'pipe velocity', -5: 'tilt', -6: 'bird velocity', 0: 'jump'}
    visualize.draw_net(config, winner, False, node_names=node_names)
    visualize.plot_stats(stat, ylog=False, view=False)

if __name__ == "__main__":
    local_dir = os.path.dirname(__file__)
    config_path = os.path.join(local_dir, 'config-feedforward.txt')
    run(config_path)