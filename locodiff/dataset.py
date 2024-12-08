import h5py
import logging
import os
import torch
from torch.utils.data import DataLoader, Dataset, Subset, random_split

import minari

log = logging.getLogger(__name__)


class ExpertDataset(Dataset):
    def __init__(
        self,
        data_directory: str | None,
        T_cond: int,
        task_name: str,
        device="cpu",
    ):
        self.T_cond = T_cond
        self.device = device

        if data_directory is not None:
            # build path
            current_dir = os.path.dirname(os.path.realpath(__file__))
            dataset_path = current_dir + "/../" + data_directory
            log.info(f"Loading data from {data_directory}")

            data = {}
            # load data
            with h5py.File(dataset_path, "r") as f:

                def load_dataset(name, obj):
                    if isinstance(obj, h5py.Dataset):
                        data[name] = obj[:]

                f.visititems(load_dataset)

            # (B, T, D)
            for k, v in data.items():
                data[k] = torch.from_numpy(v).transpose(0, 1)

            # build obs
            if task_name.startswith("Isaac-Locodiff"):
                obs = torch.cat((data["data/root_pos"], data["data/obs"]), dim=-1)
                if task_name == "Isaac-Locodiff-no-cmd":
                    obs = torch.cat([obs[..., :59], obs[..., 62:]], dim=-1)
            else:
                obs = data["data/obs"]
            # get other data
            actions = data["data/actions"]
            first_steps = data["data/first_steps"]

            # add first step flages to episode starts
            first_steps[:, 0] = 1
            # find episode ends
            first_steps_flat = first_steps.reshape(-1)
            split_indices = torch.where(first_steps_flat == 1)[0]
            # split the sequences at episode ends
            obs_splits = self.split_eps(obs, split_indices)
            actions_splits = self.split_eps(actions, split_indices)

        else:
            # TODO get this from task name
            # TODO store and load this result to speedup launch
            dataset = minari.load_dataset("D4RL/pointmaze/medium-v2")

            obs_splits, actions_splits = [], []
            for episode in dataset:
                obs_splits.append(
                    torch.tensor(episode.observations["observation"], dtype=torch.float)
                )
                actions_splits.append(torch.tensor(episode.actions, dtype=torch.float))

        self.calculate_norm_data(obs_splits, actions_splits)

        # add padding to make all sequences the same length
        max_len = max(split.shape[0] for split in obs_splits)
        obs = self.add_padding(obs_splits, max_len, temporal=True)
        actions = self.add_padding(actions_splits, max_len, temporal=True)
        masks = self.create_masks(obs_splits, max_len)

        self.data = {"obs": obs, "action": actions, "mask": masks}

        obs_size = list(self.data["obs"].shape)
        action_size = list(self.data["action"].shape)
        log.info(f"Dataset size | Observations: {obs_size} | Actions: {action_size}")

    def __len__(self):
        return len(self.data["obs"])

    def __getitem__(self, idx):
        T = self.data["mask"][idx].sum().int().item()
        return {
            key: tensor[idx, :T] for key, tensor in self.data.items() if key != "mask"
        }

    def split_eps(self, x, split_indices):
        x = torch.tensor_split(x.reshape(-1, x.shape[-1]), split_indices.tolist())
        # remove first empty split
        return x[1:]

    def add_padding(self, splits, max_len, temporal):
        x = []

        # Make all sequences the same length
        for split in splits:
            padded_split = torch.nn.functional.pad(
                split, (0, 0, 0, max_len - split.shape[0])
            )
            x.append(padded_split)
        x = torch.stack(x)

        if temporal:
            # Add initial padding to handle episode starts
            x_pad = torch.zeros_like(x[:, : self.T_cond - 1, :])
            x = torch.cat([x_pad, x], dim=1)
        else:
            # For non-temporal data, e.g. skills, just take the first timestep
            x = x[:, 0]

        return x.to(self.device)

    def create_masks(self, splits, max_len):
        masks = []

        # Create masks to indicate the padding values
        for split in splits:
            mask = torch.concatenate(
                [torch.ones(split.shape[0]), torch.zeros(max_len - split.shape[0])]
            )
            masks.append(mask)
        masks = torch.stack(masks)

        # Add initial padding to handle episode starts
        masks_pad = torch.ones((masks.shape[0], self.T_cond - 1))
        masks = torch.cat([masks_pad, masks], dim=1)

        return masks.to(self.device)

    def calculate_norm_data(self, obs_splits, actions_splits):
        all_obs = torch.cat(obs_splits)[:1000000]
        all_actions = torch.cat(actions_splits)
        # all_obs_acts = torch.cat([all_obs, all_actions], dim=-1)
        all_obs_acts = torch.cat([all_actions, all_obs], dim=-1)

        self.x_mean = all_obs.mean(0)
        self.x_std = all_obs.std(0)
        self.x_min = all_obs.min(0).values
        self.x_max = all_obs.max(0).values

        self.y_mean = all_obs_acts.mean(0)
        self.y_std = all_obs_acts.std(0)
        self.y_min = all_obs_acts.min(0).values
        self.y_max = all_obs_acts.max(0).values


class SlicerWrapper(Dataset):
    def __init__(self, dataset: Subset, T_cond: int, T: int):
        self.dataset = dataset
        self.T_cond = T_cond
        self.T = T
        self.slices = self._create_slices(T_cond, T)

    def _create_slices(self, T_cond, T):
        slices = []
        window = T_cond + T - 1
        for i in range(len(self.dataset)):
            length = len(self.dataset[i]["obs"])
            if length >= window:
                slices += [
                    (i, start, start + window) for start in range(length - window + 1)
                ]
        return slices

    def __len__(self):
        return len(self.slices)

    def __getitem__(self, idx):
        i, start, end = self.slices[idx]
        x = self.dataset[i]

        # This is to handle data without a time dimension (e.g. skills)
        return {k: v[start:end] if v.ndim > 1 else v for k, v in x.items()}


def get_dataloaders(
    task_name: str,
    data_directory: str,
    T_cond: int,
    T: int,
    train_fraction: float,
    train_batch_size: int,
    test_batch_size: int,
    num_workers: int,
):
    # Build the datasets
    dataset = ExpertDataset(data_directory, T_cond, task_name)
    train, val = random_split(dataset, [train_fraction, 1 - train_fraction])
    train_set = SlicerWrapper(train, T_cond, T)
    test_set = SlicerWrapper(val, T_cond, T)

    # Build the dataloaders
    train_dataloader = DataLoader(
        train_set,
        batch_size=train_batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True,
    )
    test_dataloader = DataLoader(
        test_set,
        batch_size=test_batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True,
    )

    return train_dataloader, test_dataloader
