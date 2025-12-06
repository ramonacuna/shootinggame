#!/usr/bin/env python3
"""
Panda3D Shooting Game with Third-Person Perspective and Background
"""

# Standard library imports
import random
import sys
import json
import os
# Panda3D imports
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import (
    CardMaker,
    Vec3,
    TransparencyAttrib,
    loadPrcFileData,
    TextNode,
    LVecBase4f
)

# Game configuration imports
from game_config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE,
    GAME_DURATION, SHOT_INTERVAL, ENEMY_SPAWN_INTERVAL,
    PLAYER_SPEED, SHOT_SPEED, EXPLOSION_DURATION,
    EXPLOSION_SPEED, BONUS_SPAWN_INTERVAL,
    SHAKE_INTENSITY, SHAKE_DURATION,
    RED_FILTER_INTENSITY, RED_FILTER_DURATION,
    LEFT_BOUND, RIGHT_BOUND, PLAYER_START_X,
    PLAYER_START_Y, ENEMY_SPAWN_Y, BONUS_SPAWN_POSITIONS,
    CAMERA_DISTANCE, CAMERA_HEIGHT, CAMERA_LOOK_AT_OFFSET,
    PLAYER_SCALE, SHOT_SCALE, EXPLOSION_SCALE,
    EXPLOSION_SCALE_MULTIPLIER, BONUS_SCALE,
    BONUS_STARTING_VALUE, BONUS_MAX_VALUE, BONUS_MIN_VALUE,
    BONUS_SPEED, BONUS_TRANSPARENCY,
    CHARACTER_IDLE_IMAGE,
    CHARACTER_LEFT_IMAGE, CHARACTER_RIGHT_IMAGE,
    SHOT_IMAGE, EXPLOSION_IMAGE,
    BONUS_POSITIVE_IMAGE, BONUS_NEGATIVE_IMAGE,
    BACKGROUND_IMAGE,
    BACKGROUND_POS_X, BACKGROUND_POS_Y, BACKGROUND_SCALE,
    ENEMY_TYPES, ENEMY_SPAWN_PROB,
    PLAYER_STARTING_LIFE,
    HIGH_SCORE_FILE, MAX_HIGH_SCORES,
    CURRENT_LEVEL, DIFFICULTY_LEVELS, CURRENT_DIFFICULTY_KEY
)

# ============================
# APPLY WINDOW CONFIGURATION
# ============================
loadPrcFileData("", f"win-size {WINDOW_WIDTH} {WINDOW_HEIGHT}")
loadPrcFileData("", f"window-title {WINDOW_TITLE}")
loadPrcFileData("", "win-fixed-size 1")


# ============================
# GAME CLASS DEFINITION
# ============================

class ShootingGame(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.disableMouse()

        self.background = self.createBackground()

        self.shots = []
        self.enemies = []
        self.explosions = []
        self.bonuses = []
        self.keyMap = {"left": False, "right": False}
        self.highScores = self.loadHighScores()

        self.gameRunning = False
        self.gameOver = True
        self.lastWin = None

        self.currentDifficultyKey = CURRENT_DIFFICULTY_KEY
        self.levelConfig = CURRENT_LEVEL
        self.playerLife = self.levelConfig["player_life"]

        self.currentShotInterval = SHOT_INTERVAL
        self.currentShotScale = SHOT_SCALE

        self.winCount = 0
        self.stage = 1

        # UI elements
        self.timerText = OnscreenText(
            text="Time: 0",
            pos=(0.05, -0.08),
            scale=0.08,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft,
            parent=base.a2dTopLeft
        )
        self.winCountText = OnscreenText(
            text="Wins: 0",
            pos=(-0.05, -0.08),
            scale=0.08,
            fg=(1, 1, 1, 1),
            align=TextNode.ARight,
            parent=base.a2dTopRight
        )
        self.lifeText = OnscreenText(
            text=f"Life: {self.playerLife}",
            pos=(0.05, -0.16),
            scale=0.08,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft,
            parent=base.a2dTopLeft
        )
        self.statusText = OnscreenText(
            text="",
            pos=(0, 0),
            scale=0.1,
            fg=(1, 0, 0, 1)
        )
        self.highScoreText = OnscreenText(
            text=self.formatHighScores(),
            pos=(0, 0.85),
            scale=0.06,
            fg=(1, 1, 0, 1),
            align=TextNode.ACenter,
            parent=base.a2dTopCenter
        )
        self.difficultyText = OnscreenText(
            text=f"Level: {self.levelConfig['name']}",
            pos=(-0.05, -0.16),
            scale=0.08,
            fg=(0, 1, 1, 1),
            align=TextNode.ARight,
            parent=base.a2dTopRight
        )

        self.menuText = OnscreenText(
            text="",
            pos=(0, 0.2),
            scale=0.1,
            fg=(1, 1, 1, 1),
            align=TextNode.ACenter
        )

        # Pre-load character textures
        self.playerTextures = {
            "idle": loader.loadTexture(CHARACTER_IDLE_IMAGE),
            "left": loader.loadTexture(CHARACTER_LEFT_IMAGE),
            "right": loader.loadTexture(CHARACTER_RIGHT_IMAGE)
        }

        # Pre-load bonus textures
        self.bonusTextures = {
            "positive": loader.loadTexture(BONUS_POSITIVE_IMAGE),
            "negative": loader.loadTexture(BONUS_NEGATIVE_IMAGE)
        }

        self.player = self.createSprite(
            self.playerTextures["idle"],
            PLAYER_START_X,
            PLAYER_START_Y,
            PLAYER_SCALE
        )
        self.player.hide()

        # Initialize camera position (Third-Person Perspective)
        self.updateCamera()
        self.originalCameraPos = self.camera.getPos()

        # Create the red filter and hide it initially
        self.redFilter = self.createRedFilter()
        self.redFilter.setAlphaScale(0.0)

        # Accept keyboard events
        self.accept("arrow_left", self.setKey, ["left", True])
        self.accept("arrow_left-up", self.setKey, ["left", False])
        self.accept("arrow_right", self.setKey, ["right", True])
        self.accept("arrow_right-up", self.setKey, ["right", False])
        self.accept("enter", self.handleEnter)
        self.accept("escape", sys.exit)

        self.accept("1", self.setDifficulty, ["EASY"])
        self.accept("2", self.setDifficulty, ["NORMAL"])
        self.accept("3", self.setDifficulty, ["HARD"])

        self.taskMgr.add(self.updateTask, "updateTask")

        self.showDifficultySelection()

    def showDifficultySelection(self):
        self.gameRunning = False
        self.gameOver = True

        self.timerText.hide()
        self.lifeText.hide()
        self.difficultyText.hide()
        self.winCountText.hide()

        menu_text = "Select Difficulty\n\n"
        for key, config in DIFFICULTY_LEVELS.items():
            icon = config.get("icon", "")
            menu_text += f"[{key[0]}] {config['name']} {icon} - Life: {config['player_life']} - Time: {config['game_duration']:.0f}s\n"

        menu_text += "\nPress 1, 2, or 3 to Start"
        self.menuText.setText(menu_text)

        self.taskMgr.remove("autoShootTask")
        self.taskMgr.remove("spawnEnemyTask")
        self.taskMgr.remove("spawnBonusTask")

    def handleEnter(self):
        if self.gameOver and not self.gameRunning:
            self.statusText.setText("")
            self.showDifficultySelection()

    def setDifficulty(self, difficulty_key):
        if self.gameRunning:
            return

        new_config = DIFFICULTY_LEVELS.get(difficulty_key)
        if new_config:
            self.currentDifficultyKey = difficulty_key
            self.levelConfig = new_config
            self.stage = 1

            self.menuText.setText(f"Starting {new_config['name']}...")
            self.statusText.setText("")

            self.restartGame()

    def loadHighScores(self):
        if os.path.exists(HIGH_SCORE_FILE):
            try:
                with open(HIGH_SCORE_FILE, 'r') as f:
                    return json.load(f)
            except (IOError, json.JSONDecodeError):
                return []
        return []

    def saveHighScores(self):
        self.highScores.sort(reverse=True)
        self.highScores = self.highScores[:MAX_HIGH_SCORES]
        try:
            with open(HIGH_SCORE_FILE, 'w') as f:
                json.dump(self.highScores, f)
        except IOError:
            pass

    def formatHighScores(self):
        sorted_scores = sorted(self.highScores, reverse=True)[:MAX_HIGH_SCORES]
        text = "🏆 Best Survival Times (s) 🏆\n"
        if not sorted_scores:
            text += "Play to set a record!"
        else:
            for i, time in enumerate(sorted_scores):
                text += f"{i + 1}. {time:.1f}s\n"
        return text.strip()

    def createRedFilter(self):
        cm = CardMaker("red_filter")
        cm.setFrameFullscreenQuad()
        filter_node = render2d.attachNewNode(cm.generate())
        filter_node.setColor(LVecBase4f(1, 0, 0, RED_FILTER_INTENSITY))
        filter_node.setTransparency(TransparencyAttrib.MAlpha)
        return filter_node

    def startScreenShake(self):
        self.shakeStartTime = globalClock.getFrameTime()
        self.taskMgr.add(self.shakeTask, "shakeTask")

    def shakeTask(self, task):
        currentTime = globalClock.getFrameTime()
        elapsed = currentTime - self.shakeStartTime

        if elapsed < SHAKE_DURATION:
            decay = 1.0 - (elapsed / SHAKE_DURATION)
            intensity = SHAKE_INTENSITY * decay

            shake_x = random.uniform(-intensity, intensity)
            shake_y = random.uniform(-intensity, intensity)

            self.camera.setPos(self.originalCameraPos + Vec3(shake_x, shake_y, 0))
            return Task.cont
        else:
            self.camera.setPos(self.originalCameraPos)
            return Task.done

    def showRedFilter(self):
        self.redFilter.setAlphaScale(RED_FILTER_INTENSITY)
        self.taskMgr.doMethodLater(RED_FILTER_DURATION, self.hideRedFilter, "hideRedFilter")

    def hideRedFilter(self, task):
        self.redFilter.setAlphaScale(0.0)
        return Task.done

    def createBackground(self):
        bg_tex = loader.loadTexture(BACKGROUND_IMAGE)
        cm = CardMaker("background")
        cm.setFrame(-1, 1, -1, 1)
        bg = render.attachNewNode(cm.generate())
        bg.setTexture(bg_tex)
        bg.setPos(BACKGROUND_POS_X, BACKGROUND_POS_Y, 0)
        bg.setScale(BACKGROUND_SCALE)
        bg.setBin("background", 0)
        bg.setDepthTest(False)
        bg.setDepthWrite(False)
        return bg

    def createSprite(self, texture, x, y, scale=1.0, transparency=1.0):
        cm = CardMaker("sprite")
        cm.setFrame(-0.5, 0.5, -0.5, 0.5)
        sprite = render.attachNewNode(cm.generate())
        sprite.setTexture(texture)
        sprite.setTransparency(TransparencyAttrib.MAlpha)
        sprite.setAlphaScale(transparency)
        sprite.setBillboardPointEye()
        sprite.setScale(scale)
        sprite.setPos(x, y, 0)
        return sprite

    def createExplosionSprite(self, x, y, enemy_scale=None, speed=EXPLOSION_SPEED):
        explosion_tex = loader.loadTexture(EXPLOSION_IMAGE)

        if enemy_scale:
            explosion_scale = enemy_scale * EXPLOSION_SCALE_MULTIPLIER
        else:
            explosion_scale = EXPLOSION_SCALE

        explosion_sprite = self.createSprite(explosion_tex, x, y, explosion_scale)
        explosion_sprite.setPythonTag("speed", speed)
        return explosion_sprite

    def createBonusSprite(self, x, y, value=BONUS_STARTING_VALUE, scale=BONUS_SCALE, speed=BONUS_SPEED):
        texture = self.bonusTextures["positive"] if value >= 0 else self.bonusTextures["negative"]

        bonus_sprite = self.createSprite(texture, x, y, scale, BONUS_TRANSPARENCY)
        bonus_sprite.setPythonTag("value", value)
        bonus_sprite.setPythonTag("speed", speed)
        bonus_sprite.setPythonTag("scale", scale)

        horiz_scale = (RIGHT_BOUND - LEFT_BOUND)
        bonus_sprite.setScale(horiz_scale, scale, scale)

        text = OnscreenText(
            text=str(value),
            scale=0.2,
            fg=(1, 1, 1, 1),
            align=TextNode.ACenter,
            mayChange=True,
            parent=bonus_sprite
        )

        text.setPos(0, -0.06)
        text.setBin('fixed', 1)
        text.setDepthTest(False)
        text.setDepthWrite(False)

        bonus_sprite.setPythonTag("text", text)

        return bonus_sprite

    def removeExplosionTask(self, explosion_sprite):
        explosion_sprite.removeNode()
        if explosion_sprite in self.explosions:
            self.explosions.remove(explosion_sprite)
        return Task.done

    def setKey(self, key, value):
        self.keyMap[key] = value
        if self.gameRunning:
            self.updatePlayerTexture()

    def updatePlayerTexture(self):
        if self.keyMap["left"]:
            self.player.setTexture(self.playerTextures["left"])
        elif self.keyMap["right"]:
            self.player.setTexture(self.playerTextures["right"])
        else:
            self.player.setTexture(self.playerTextures["idle"])

    def updateTask(self, task):
        if not self.gameRunning:
            return Task.cont

        if self.gameOver:
            return Task.cont

        dt = globalClock.getDt()
        self.updatePlayer(dt)
        self.updateShots(dt)
        self.updateEnemies(dt)
        self.updateExplosions(dt)
        self.updateBonuses(dt)
        self.checkCollisions()
        self.updateCamera()

        # Game Timer
        elapsed = globalClock.getRealTime() - self.gameStartTime
        self.timerText.setText(f"Time: {elapsed:.1f}")

        if elapsed >= self.levelConfig["game_duration"]:
            self.endGame(win=True)
        elif self.playerLife <= 0:
            self.endGame(win=False)
        return Task.cont

    def updatePlayer(self, dt):
        dx = 0
        if self.keyMap["left"]:
            dx -= PLAYER_SPEED * dt
        if self.keyMap["right"]:
            dx += PLAYER_SPEED * dt
        newX = self.player.getX() + dx
        self.player.setX(max(LEFT_BOUND, min(RIGHT_BOUND, newX)))

    def updateCamera(self):
        playerX = self.player.getX()
        self.camera.setPos(playerX, PLAYER_START_Y - CAMERA_DISTANCE,
                           CAMERA_HEIGHT)
        self.camera.lookAt(playerX, PLAYER_START_Y + CAMERA_LOOK_AT_OFFSET, 0)
        self.originalCameraPos = self.camera.getPos()

    def updateShots(self, dt):
        for shot in self.shots[:]:
            shot.setY(shot.getY() + SHOT_SPEED * dt)
            if shot.getY() > ENEMY_SPAWN_Y + 5:
                shot.removeNode()
                self.shots.remove(shot)

    def takeDamage(self):
        self.playerLife -= 1
        self.lifeText.setText(f"Life: {self.playerLife}")
        self.startScreenShake()
        self.showRedFilter()
        if self.playerLife <= 0:
            self.endGame(win=False)

    def updateEnemies(self, dt):
        for enemy in self.enemies[:]:
            speed = enemy.getPythonTag("speed")
            enemy.setY(enemy.getY() - speed * dt)

            should_remove_enemy = False
            damage_taken = False

            if enemy.getY() <= PLAYER_START_Y:

                if abs(enemy.getX() - self.player.getX()) < 1.0:
                    self.takeDamage()
                    should_remove_enemy = True
                    damage_taken = True

                if enemy.getY() < PLAYER_START_Y and not damage_taken:
                    self.takeDamage()
                    should_remove_enemy = True

            if should_remove_enemy:
                enemy.removeNode()
                self.enemies.remove(enemy)
                continue

    def updateBonuses(self, dt):
        for bonus in self.bonuses[:]:
            speed = bonus.getPythonTag("speed")
            bonus.setY(bonus.getY() - speed * dt)

            if bonus.getY() <= PLAYER_START_Y:
                if abs(bonus.getX() - self.player.getX()) < 1.0:
                    self.applyBonusEffect(bonus.getPythonTag("value"))
                text = bonus.getPythonTag("text")
                if text:
                    text.destroy()
                bonus.removeNode()
                self.bonuses.remove(bonus)
                continue

            if bonus.getY() < PLAYER_START_Y - 10:
                text = bonus.getPythonTag("text")
                if text:
                    text.destroy()
                bonus.removeNode()
                self.bonuses.remove(bonus)

    def applyBonusEffect(self, value):
        if value == -10:
            modifier = 0.5
        elif value == 0:
            modifier = 1.0
        elif value == 10:
            modifier = 2.0
        else:
            modifier = 0.5 + ((value - BONUS_MIN_VALUE) / (BONUS_MAX_VALUE - BONUS_MIN_VALUE)) * 1.5

        self.currentShotInterval = SHOT_INTERVAL / modifier
        self.currentShotScale = SHOT_SCALE * modifier

        self.taskMgr.remove("autoShootTask")
        self.taskMgr.doMethodLater(self.currentShotInterval, self.autoShootTask, "autoShootTask")

    def updateExplosions(self, dt):
        for explosion in self.explosions[:]:
            speed = explosion.getPythonTag("speed")
            explosion.setY(explosion.getY() - speed * dt)
            if explosion.getY() < PLAYER_START_Y - 10:
                explosion.removeNode()
                self.explosions.remove(explosion)

    def checkCollisions(self):
        for shot in self.shots[:]:
            shotPos = shot.getPos()
            shot_to_remove = False

            for enemy in self.enemies[:]:
                enemyPos = enemy.getPos()
                if (shotPos - enemyPos).length() < 0.55:
                    hp = enemy.getPythonTag("hp")
                    enemy.setPythonTag("hp", hp - 1)
                    shot_to_remove = True
                    if enemy.getPythonTag("hp") <= 0:
                        enemy_scale = enemy.getScale().x
                        explosion = self.createExplosionSprite(
                            enemy.getX(),
                            enemy.getY(),
                            enemy_scale=enemy_scale
                        )
                        self.explosions.append(explosion)
                        self.taskMgr.doMethodLater(EXPLOSION_DURATION,
                                                   self.removeExplosionTask,
                                                   "removeExplosionTask",
                                                   extraArgs=[explosion])
                        enemy.removeNode()
                        self.enemies.remove(enemy)
                        break

            if shot_to_remove:
                shot.removeNode()
                self.shots.remove(shot)
                continue

            for bonus in self.bonuses[:]:
                bonusPos = bonus.getPos()
                if (shotPos - bonusPos).length() < 2:
                    value = bonus.getPythonTag("value")
                    new_value = min(value + 1, BONUS_MAX_VALUE)

                    bonus.setPythonTag("value", new_value)

                    if new_value > 0:
                        bonus.setTexture(self.bonusTextures["positive"])
                    else:
                        bonus.setTexture(self.bonusTextures["negative"])

                    text = bonus.getPythonTag("text")
                    if text:
                        text.setText(str(new_value))

                    shot.removeNode()
                    self.shots.remove(shot)
                    break

    def autoShootTask(self, task):
        if self.gameRunning and not self.gameOver:
            shot = self.createSprite(loader.loadTexture(SHOT_IMAGE),
                                     self.player.getX(), self.player.getY(), self.currentShotScale)
            self.shots.append(shot)
        return Task.again

    def getEnemySpawnInterval(self):
        base_interval = self.levelConfig["enemy_spawn_interval"]
        return max(0.1, base_interval - (0.1 * (self.stage - 1)))

    def spawnEnemyTask(self, task):
        if not self.gameRunning or self.gameOver:
            return Task.done

        etype = random.choices(list(ENEMY_TYPES.keys()), ENEMY_SPAWN_PROB)[0]
        enemyX = random.uniform(LEFT_BOUND, RIGHT_BOUND)
        enemy = self.createSprite(loader.loadTexture(ENEMY_TYPES[etype]["image"]),
                                  enemyX, ENEMY_SPAWN_Y, ENEMY_TYPES[etype]["scale"])
        enemy.setPythonTag("hp", ENEMY_TYPES[etype]["hp"])
        enemy.setPythonTag("speed", ENEMY_TYPES[etype]["speed"])
        self.enemies.append(enemy)

        return Task.again

    def spawnBonusTask(self, task):
        if not self.gameRunning or self.gameOver:
            return Task.done

        bonusX = random.choice(BONUS_SPAWN_POSITIONS)

        bonus = self.createBonusSprite(
            bonusX,
            ENEMY_SPAWN_Y,
            value=BONUS_STARTING_VALUE,
            scale=BONUS_SCALE,
            speed=BONUS_SPEED
        )
        self.bonuses.append(bonus)
        return Task.again

    def endGame(self, win):
        self.gameOver = True
        self.gameRunning = False
        self.lastWin = win

        self.player.hide()
        self.taskMgr.remove("autoShootTask")
        self.taskMgr.remove("spawnEnemyTask")
        self.taskMgr.remove("spawnBonusTask")
        self.taskMgr.remove("restartGameTask")

        if win:
            finalTime = globalClock.getRealTime() - self.gameStartTime
            if finalTime >= self.levelConfig["game_duration"]:
                self.highScores.append(finalTime)
                self.saveHighScores()
                self.highScoreText.setText(self.formatHighScores())

            self.winCount += 1
            self.stage += 1
            self.winCountText.setText(f"Wins: {self.winCount}")
            self.statusText.setText(f"You Win! Stage {self.stage} starting soon...")
            self.taskMgr.doMethodLater(3.0, self.restartGameTask, "restartGameTask", extraArgs=[True])
        else:
            self.statusText.setText("Game Over! Click Enter to play again.")
            self.stage = 1

    def restartGameTask(self, task, next_stage=False):
        self.restartGame(next_stage)
        return Task.done

    def restartGame(self, next_stage=False):
        if not self.gameRunning:
            for shot in self.shots:
                shot.removeNode()
            self.shots = []

            for enemy in self.enemies:
                enemy.removeNode()
            self.enemies = []

            for explosion in self.explosions:
                explosion.removeNode()
            self.explosions = []

            for bonus in self.bonuses:
                text = bonus.getPythonTag("text")
                if text:
                    text.destroy()
                bonus.removeNode()
            self.bonuses = []

            self.playerLife = self.levelConfig["player_life"]

            self.currentShotInterval = SHOT_INTERVAL
            self.currentShotScale = SHOT_SCALE

            self.timerText.show()
            self.lifeText.show()
            self.difficultyText.show()
            self.winCountText.show()
            self.menuText.setText("")
            self.statusText.setText("")

            self.player.show()
            self.player.setPos(PLAYER_START_X, PLAYER_START_Y, 0)
            self.player.setTexture(self.playerTextures["idle"])
            self.lifeText.setText(f"Life: {self.playerLife}")
            self.difficultyText.setText(
                f"Level: {self.levelConfig['name']} - Stage {self.stage}")

            self.gameStartTime = globalClock.getRealTime()
            self.timerText.setText("Time: 0")
            self.gameOver = False
            self.gameRunning = True
            self.lastWin = None

            self.taskMgr.remove("autoShootTask")
            self.taskMgr.remove("spawnEnemyTask")
            self.taskMgr.remove("spawnBonusTask")

            enemy_interval = self.getEnemySpawnInterval()
            self.taskMgr.doMethodLater(self.currentShotInterval, self.autoShootTask, "autoShootTask")
            self.taskMgr.doMethodLater(enemy_interval, self.spawnEnemyTask, "spawnEnemyTask")
            self.taskMgr.doMethodLater(BONUS_SPAWN_INTERVAL, self.spawnBonusTask, "spawnBonusTask")


game = ShootingGame()
game.run()