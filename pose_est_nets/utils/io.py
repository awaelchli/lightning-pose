"""Path handling functions."""

from omegaconf import DictConfig, OmegaConf, ListConfig
import os
from typeguard import typechecked
from typing import Any, Tuple, Union


@typechecked
def ckpt_path_from_base_path(
    base_path: str,
    model_name: str,
    logging_dir_name: str = "tb_logs/",
    version: int = 0,
) -> str:
    """Given a path to a hydra output with trained model, extract the model .ckpt file.

    Args:
        base_path (str): path to a folder with logs and checkpoint. for example,
            function will search base_path/logging_dir_name/model_name...
        model_name (str): the name you gave your model before training it; appears as
            model_name in lightning-pose/scripts/config/model_params.yaml
        logging_dir_name (str, optional): name of the folder in logs, controlled in
            train_hydra.py Defaults to "tb_logs/".
        version (int. optional):

    Returns:
        str: path to model checkpoint

    """
    # TODO: consider finding the most recent hydra path containing logging_dir_name
    import glob
    model_search_path = os.path.join(
        base_path,
        logging_dir_name,  # TODO: may change when we switch from Tensorboard
        model_name,  # get the name string of the model (determined pre-training)
        "version_%i" % version,  # always version_0 because ptl starts a version_0 dir
        "checkpoints",
        "*.ckpt",
    )
    # TODO: we're taking the last ckpt. make sure that with multiple checkpoints, this
    # is what we want
    model_ckpt_path = glob.glob(model_search_path)[-1]
    return model_ckpt_path


@typechecked
def check_if_semi_supervised(
        losses_to_use: Union[ListConfig, list, None] = None
) -> bool:
    """Use config file to determine if model is semi-supervised.

    Take the entry of the hydra cfg that specifies losses_to_use. If it contains
    meaningful entries, infer that we want a semi_supervised model.

    Args:
        losses_to_use (Union[ListConfig, list, None], optional): the cfg entry
            specifying semisupervised losses to use. Defaults to None.

    Returns:
        bool: True if the model is semi_supervised. False otherwise.

    """
    if losses_to_use is None:  # null
        semi_supervised = False
    elif len(losses_to_use) == 0:  # empty list
        semi_supervised = False
    elif (
        len(losses_to_use) == 1 and losses_to_use[0] == ""
    ):  # list with an empty string
        semi_supervised = False
    else:
        semi_supervised = True
    return semi_supervised


def format_and_update_loss_info(cfg):
    loss_param_dict = OmegaConf.to_object(cfg.losses)
    losses_to_use = OmegaConf.to_object(cfg.model.losses_to_use)
    if "pca_multiview" in losses_to_use:
        loss_param_dict["pca_multiview"][
            "mirrored_column_matches"
        ] = cfg.data.mirrored_column_matches
    if "unimodal" in losses_to_use:
        if cfg.model.model_type == "regression":
            raise NotImplementedError(
                f"unimodal loss can only be used with classes inheriting from "
                f"HeatmapTracker. \nYou specified an invalid RegressionTracker model."
            )
        downsample_scale = 2 ** cfg.data.downsample_factor
        output_shape = (
            cfg.data.image_resize_dims.height // downsample_scale,
            cfg.data.image_resize_dims.width // downsample_scale,
        )
        loss_param_dict["unimodal"]["output_shape"] = output_shape
        loss_param_dict["unimodal"][
            "original_image_height"
        ] = cfg.data.image_resize_dims.height
        loss_param_dict["unimodal"][
            "original_image_width"
        ] = cfg.data.image_resize_dims.width
        loss_param_dict["unimodal"]["heatmap_loss_type"] = cfg.model.heatmap_loss_type

    return loss_param_dict, losses_to_use


# --------------------------------------------------------------------------------------
# Path handling functions for running toy dataset
# --------------------------------------------------------------------------------------


@typechecked
def return_absolute_path(possibly_relative_path: str, n_dirs_back=3) -> str:
    """Return absolute path from possibly relative path."""
    if os.path.isabs(possibly_relative_path):
        # absolute path already; do nothing
        abs_path = possibly_relative_path
    else:
        # our toy_dataset in relative path
        cwd_split = os.getcwd().split(os.path.sep)
        desired_path_list = cwd_split[:-n_dirs_back]
        abs_path = os.path.join(os.path.sep, *desired_path_list, possibly_relative_path)
    if not os.path.exists(abs_path):
        raise IOError("%s is not a valid path" % abs_path)
    return abs_path


@typechecked
def return_absolute_data_paths(data_cfg: DictConfig) -> Tuple[str, str]:
    """Generate absolute path for our example toy data.

    @hydra.main decorator switches the cwd when executing the decorated function, e.g.,
    our train(). so we're in some /outputs/YYYY-MM-DD/HH-MM-SS folder.

    Args:
        data_cfg (DictConfig): data config file with paths to data and video folders.

    Returns:
        Tuple[str, str]: absolute paths to data and video folders.

    """
    data_dir = return_absolute_path(data_cfg.data_dir)
    if os.path.isabs(data_cfg.video_dir):
        video_dir = data_cfg.video_dir
    else:
        video_dir = os.path.join(data_dir, data_cfg.video_dir)
    # assert that those paths exist and in the proper format
    assert os.path.isdir(data_dir)
    assert os.path.isdir(video_dir) or os.path.isfile(video_dir)
    return data_dir, video_dir
