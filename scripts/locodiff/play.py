# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Script to play a checkpoint if an RL agent from RSL-RL."""

"""Launch Isaac Sim Simulator first."""

import argparse
import sys

from omni.isaac.lab.app import AppLauncher

# local imports
import cli_args  # isort: skip

# add argparse arguments
parser = argparse.ArgumentParser(description="Train an RL agent with RSL-RL.")
parser.add_argument(
    "--video", action="store_true", default=False, help="Record videos during training."
)
parser.add_argument(
    "--video_length",
    type=int,
    default=200,
    help="Length of the recorded video (in steps).",
)
parser.add_argument(
    "--disable_fabric",
    action="store_true",
    default=False,
    help="Disable fabric and use USD I/O operations.",
)
parser.add_argument(
    "--num_envs", type=int, default=1, help="Number of environments to simulate."
)
# append RSL-RL cli arguments
cli_args.add_rsl_rl_args(parser)
# append AppLauncher cli args
AppLauncher.add_app_launcher_args(parser)
args_cli, hydra_args = parser.parse_known_args()
# always enable cameras to record video
if args_cli.video:
    args_cli.enable_cameras = True

sys.argv = [sys.argv[0]] + hydra_args
sys.argv.append("hydra.output_subdir=null")
sys.argv.append("hydra.run.dir=.")

# launch omniverse app
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

"""Rest everything follows."""

import gymnasium as gym
import matplotlib.pylab as plt
import os
import statistics
import torch

from omegaconf import DictConfig

from omni.isaac.lab.envs import ManagerBasedRLEnvCfg
from omni.isaac.lab_tasks.utils.wrappers.rsl_rl import RslRlVecEnvWrapper

import isaac_ext.tasks  # noqa: F401
from locodiff.runner import DiffusionRunner
from locodiff.utils import dynamic_hydra_main
from vae.utils import get_latest_run


def plot(root_pos, obs, root_pos_traj, ax):
    # collect real and pred positions
    root_pos.append(obs[:, :2])
    root_pos_traj = root_pos_traj[0].cpu().numpy()
    # reset plot
    ax.clear()
    ax.set_xlim(-4, 4)
    ax.set_ylim(-4, 4)
    # plot trajectories
    root_pos_curr = torch.cat(root_pos, dim=0).cpu().numpy()
    ax.plot(root_pos_curr[:, 0], root_pos_curr[:, 1], "b")
    ax.plot(root_pos_traj[:, 0], root_pos_traj[:, 1], "r--")
    plt.draw()
    plt.pause(0.01)

    return root_pos


task = "Isaac-Cartpole-Diffusion"


@dynamic_hydra_main(task)
def main(agent_cfg: DictConfig, env_cfg: ManagerBasedRLEnvCfg):
    """Play with RSL-RL agent."""
    if args_cli.num_envs is not None:
        env_cfg.scene.num_envs = args_cli.num_envs
        agent_cfg.num_envs = args_cli.num_envs
    env_cfg.episode_length_s = agent_cfg.episode_length
    agent_cfg.dataset.task_name = task

    # create isaac environment
    env = gym.make(
        task, cfg=env_cfg, render_mode="rgb_array" if args_cli.video else None
    )

    # wrap around environment for rsl-rl
    env = RslRlVecEnvWrapper(env)
    agent_cfg.obs_dim = env.observation_space["policy"].shape[-1]
    agent_cfg.act_dim = env.action_space.shape[-1]

    # load previously trained model
    runner = DiffusionRunner(env, agent_cfg, device=agent_cfg.device)

    # load the checkpoint
    log_root_path = os.path.abspath("logs/diffusion/cartpole")
    resume_path = os.path.join(get_latest_run(log_root_path), "models", "model.pt")
    print(f"[INFO]: Loading model checkpoint from: {resume_path}")
    runner.load(resume_path)

    # test_loss = []
    # for batch in runner.test_loader:
    #     test_loss.append(runner.policy.test(batch))
    # test_loss = statistics.mean(test_loss)
    # print(f"Test loss: {test_loss}")
    # exit()

    # obtain the trained policy for inference
    policy = runner.get_inference_policy(device=env.unwrapped.device)

    # create figure
    # plt.ion()
    # _, ax = plt.subplots()
    # ax.set_xlim(-4, 4)
    # ax.set_ylim(-4, 4)
    # root_pos = []

    # reset environment
    obs, _ = env.get_observations()
    timestep = 0
    # simulate environment
    while simulation_app.is_running():
        # run everything in inference mode
        with torch.inference_mode():
            # agent stepping
            actions = policy({"obs": obs})
            # env stepping
            obs, _, dones, _ = env.step(actions)

        if dones.any():
            runner.policy.reset(dones)

        # root_pos = plot(root_pos, obs, root_pos_traj, ax)
        timestep += 1

    # close the simulator
    env.close()


if __name__ == "__main__":
    # run the main function
    main()
    # close sim app
    simulation_app.close()
