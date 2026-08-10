import pytest

from adpaper.models import Paper
from plugins.autonomous_driving import plugin


def test_driving_paper_is_included_and_tagged():
    paper = Paper(
        arxiv_id="2608.00001",
        title="Camera-LiDAR BEV Fusion for Autonomous Driving",
        abstract="We evaluate on nuScenes for 3D object detection.",
        categories=["cs.CV"],
    )
    result = plugin.evaluate(paper)
    tags = plugin.assign_tags(paper)
    assert result.include
    assert result.score > 0
    assert tags.primary in plugin.tags
    assert len(tags.secondary) <= 2


def test_non_driving_medical_paper_is_excluded():
    paper = Paper(
        arxiv_id="2608.00002",
        title="Medical Image Segmentation with Diffusion",
        abstract="A healthcare diagnosis benchmark.",
        categories=["cs.CV"],
    )
    assert not plugin.evaluate(paper).include


@pytest.mark.parametrize(
    ("title", "abstract"),
    [
        (
            "Autonomous UUV Navigation with 4D Radar Perception",
            "An underwater scene understanding method for unmanned underwater vehicles.",
        ),
        (
            "BEV Perception for Robot Manipulation",
            "A robotic grasping system evaluated on tabletop scenes.",
        ),
        (
            "Road-like Structure Detection for Medical Diagnosis",
            "We segment vascular structures in pathology images.",
        ),
        (
            "Self-Driving Microscopy with Visual Localization",
            "An automated microscope navigates biological samples.",
        ),
        (
            "Industrial Anomaly Detection with Scene Completion",
            "A factory inspection benchmark for manufacturing defects.",
        ),
        (
            "Self-Driving Liquid Handling Laboratory",
            "A robotic assay platform for molecular biology.",
        ),
        (
            "Trustworthy Embodied Intelligence",
            "A general robotics framework drawing on autonomous driving.",
        ),
        (
            "Robotic Failure Analysis in Chemical Self-Driving Laboratories",
            "A benchmark for automated chemistry experiments.",
        ),
        (
            "UAV-Assisted Emergency Networks",
            "Multi-agent trajectory control for aerial communications.",
        ),
        (
            "Fine-Grained Vehicle Damage Assessment",
            "Automated inspection of scratches and cracks.",
        ),
        (
            "From Sports to Safety",
            "A sports-video benchmark inspired by autonomous driving.",
        ),
    ],
)
def test_non_driving_near_matches_are_excluded(title, abstract):
    paper = Paper(
        arxiv_id="2608.00003",
        title=title,
        abstract=abstract,
        categories=["cs.CV"],
    )
    assert not plugin.evaluate(paper).include


def test_generic_scene_method_is_not_enough_without_driving_context():
    paper = Paper(
        arxiv_id="2608.00004",
        title="Generic Scene Completion with BEV Features",
        abstract="A general perception method for indoor environments.",
        categories=["cs.CV"],
    )
    assert not plugin.evaluate(paper).include


def test_road_domain_specific_title_keeps_high_recall():
    paper = Paper(
        arxiv_id="2608.00005",
        title="Robust 4D Radar Odometry",
        abstract="We estimate motion from sparse radar point measurements.",
        categories=["cs.RO"],
    )
    assert plugin.evaluate(paper).include


@pytest.mark.parametrize(
    "abstract",
    [
        "Perception for autonomous vehicles in adverse weather.",
        "Collaborative 3D detection evaluated on DAIR-V2X and V2XSet.",
    ],
)
def test_vehicle_and_v2x_signals_keep_high_recall(abstract):
    paper = Paper(
        arxiv_id="2608.00006",
        title="Multi-Sensor Perception Framework",
        abstract=abstract,
        categories=["cs.CV"],
    )
    assert plugin.evaluate(paper).include
