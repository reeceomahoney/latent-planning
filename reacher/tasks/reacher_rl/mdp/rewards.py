import torch

from omni.isaac.lab.assets import RigidObject
from omni.isaac.lab.envs import ManagerBasedRLEnv
from omni.isaac.lab.managers import SceneEntityCfg
from omni.isaac.lab.utils.math import (
    combine_frame_transforms,
    quat_error_magnitude,
    quat_mul,
)


def position_command_error(
    env: ManagerBasedRLEnv,
    command_name: str,
    asset_cfg: SceneEntityCfg,
    sigma: float = 0.1,
) -> torch.Tensor:
    """Penalize tracking of the position error using L2-norm.

    The function computes the position error between the desired position (from the command) and the
    current position of the asset's body (in world frame). The position error is computed as the L2-norm
    of the difference between the desired and current positions.
    """
    # extract the asset (to enable type hinting)
    asset: RigidObject = env.scene[asset_cfg.name]
    command = env.command_manager.get_command(command_name)
    # obtain the desired and current positions
    des_pos_b = command[:, :3]
    des_pos_w, _ = combine_frame_transforms(
        asset.data.root_state_w[:, :3], asset.data.root_state_w[:, 3:7], des_pos_b
    )
    curr_pos_w = asset.data.body_state_w[:, asset_cfg.body_ids[0], :3]  # type: ignore
    return torch.exp(-((torch.norm(curr_pos_w - des_pos_w, dim=1) / sigma) ** 2))


def orientation_command_error(
    env: ManagerBasedRLEnv, command_name: str, asset_cfg: SceneEntityCfg
) -> torch.Tensor:
    """Penalize tracking orientation error using shortest path.

    The function computes the orientation error between the desired orientation (from the command) and the
    current orientation of the asset's body (in world frame). The orientation error is computed as the shortest
    path between the desired and current orientations.
    """
    # extract the asset (to enable type hinting)
    asset: RigidObject = env.scene[asset_cfg.name]
    command = env.command_manager.get_command(command_name)
    # obtain the desired and current orientations
    des_quat_b = command[:, 3:7]
    des_quat_w = quat_mul(asset.data.root_state_w[:, 3:7], des_quat_b)
    curr_quat_w = asset.data.body_state_w[:, asset_cfg.body_ids[0], 3:7]  # type: ignore
    return torch.exp(-quat_error_magnitude(curr_quat_w, des_quat_w))
