import gymnasium as gym
import numpy as np
import torch

import gymnasium_robotics

gym.register_envs(gymnasium_robotics)


class MazeEnv:
    def __init__(self, agent_cfg, render=False):
        render_mode = "human" if render else None
        self.env = gym.make(
            agent_cfg.task,
            max_episode_steps=int(agent_cfg.episode_length * 100),
            render_mode=render_mode,
        )
        self.obs = None
        self.goal = None
        self.device = agent_cfg.device

        self.obs_dim = self.env.observation_space["observation"].shape[0]  # type: ignore
        self.act_dim = self.env.action_space.shape[0]  # type: ignore
        self.num_envs = 1

    def reset(self):
        obs, _ = self.env.reset()
        self.obs = self.to_tensor(obs["observation"])
        self.goal = self.to_tensor(obs["desired_goal"])
        return self.obs

    def step(self, action):
        action = action[0].cpu().numpy()

        obs, reward, terminated, trunacted, info = self.env.step(action)

        self.obs = self.to_tensor(obs["observation"])
        reward = self.to_tensor(reward)
        dones = terminated | trunacted
        dones = torch.tensor(dones).to(dtype=torch.long).unsqueeze(0)

        return self.obs, reward, dones, info

    def get_observations(self):
        return self.obs, None

    def render(self):
        self.env.render()

    def close(self):
        self.env.close()

    def get_maze(self):
        maze = np.array(self.env.unwrapped.maze.maze_map)
        return 1 - maze

    def to_tensor(self, x):
        return torch.tensor(x, dtype=torch.float, device=self.device).unsqueeze(0)
