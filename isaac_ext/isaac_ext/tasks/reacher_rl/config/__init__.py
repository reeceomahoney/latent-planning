import gymnasium as gym
from . import rl_env_cfg
from .locodiff import locodiff_env_cfg
from .no_cmd import no_cmd_env_cfg

gym.register(
    id="Isaac-Reacher-RL",
    entry_point="omni.isaac.lab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": rl_env_cfg.ReacherRLEnvCfg,
        "agent_cfg_entry_point": "reacher.config.rl_cfg:ReacherPPORunnerCfg",
    },
)

gym.register(
    id="Isaac-Reacher-RL-Play",
    entry_point="omni.isaac.lab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": rl_env_cfg.ReacherRLEnvCfg_PLAY,
        "agent_cfg_entry_point": "reacher.config.rl_cfg:ReacherPPORunnerCfg",
    },
)

gym.register(
    id="Isaac-Reacher-RL-Flat",
    entry_point="omni.isaac.lab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": rl_env_cfg.ReacherRLFlatEnvCfg,
        "agent_cfg_entry_point": "reacher.config.rl_cfg:ReacherFlatPPORunnerCfg",
    },
)
gym.register(
    id="Isaac-Reacher-RL-Flat-Play",
    entry_point="omni.isaac.lab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": rl_env_cfg.ReacherRLFlatEnvCfg_PLAY,
        "agent_cfg_entry_point": "reacher.config.rl_cfg:ReacherFlatPPORunnerCfg",
    },
)
gym.register(
    id="Isaac-Locodiff",
    entry_point="omni.isaac.lab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": locodiff_env_cfg.LocodiffEnvCfg,
        "agent_cfg_entry_point": "reacher.config.rl_cfg:ReacherPPORunnerCfg",
    },
)

gym.register(
    id="Isaac-Locodiff-no-cmd",
    entry_point="omni.isaac.lab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": no_cmd_env_cfg.LocodiffEnvCfg,
    },
)
