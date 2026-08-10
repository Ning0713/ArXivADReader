from __future__ import annotations

import re
from dataclasses import dataclass

from adpaper.models import Paper, RelevanceResult, TagAssignment


def _normalized_text(paper: Paper) -> str:
    return " ".join(
        [paper.title, paper.title_zh, paper.abstract, paper.abstract_zh, " ".join(paper.categories)]
    ).casefold()


def _matches(text: str, terms: tuple[str, ...]) -> list[str]:
    matches: list[str] = []
    for term in terms:
        normalized = term.casefold()
        if re.search(r"[a-z0-9]", normalized):
            pattern = rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])"
            if re.search(pattern, text):
                matches.append(term)
        elif normalized in text:
            matches.append(term)
    return matches


@dataclass(slots=True)
class AutonomousDrivingPlugin:
    slug: str = "autonomous-driving"
    version: str = "autonomous-driving-v2"
    display_name: str = "自动驾驶"
    minimum_weak_score: float = 12.0
    tags: tuple[str, ...] = (
        "感知",
        "3D 检测",
        "BEV/Occupancy",
        "多传感器融合",
        "LiDAR/点云",
        "Radar",
        "深度/几何",
        "地图/定位",
        "预测/规划",
        "端到端驾驶",
        "VLM/VLA",
        "世界模型/生成",
        "仿真/数据",
        "安全/异常",
        "协同/V2X",
    )

    explicit_terms: tuple[str, ...] = (
        "autonomous driving",
        "automated driving",
        "self-driving",
        "driverless",
        "autonomous vehicle",
        "autonomous vehicles",
        "automated vehicle",
        "automated vehicles",
        "connected autonomous vehicle",
        "connected automated vehicle",
        "autonomous racing",
        "vehicle-to-everything",
        "v2x",
        "end-to-end driving",
        "driving scene",
        "driving perception",
        "driving policy",
        "ego-vehicle",
        "ego vehicle",
        "智能驾驶",
        "自动驾驶",
        "无人驾驶",
    )
    dataset_terms: tuple[str, ...] = (
        "nuscenes",
        "kitti",
        "waymo open",
        "argoverse",
        "pandaset",
        "bdd100k",
        "once dataset",
        "opendrivelab",
        "openlane",
        "carla",
        "driveseg",
        "cityscapes",
        "dair-v2x",
        "v2xset",
        "opv2v",
        "v2v4real",
        "tumtraf",
        "nuplan",
        "kitti-360",
        "semantickitti",
        "a2d2",
    )
    context_terms: tuple[str, ...] = (
        "autonomous",
        "driving",
        "self-driving car",
        "autonomous vehicle",
        "vehicle",
        "car",
        "automotive",
        "traffic",
        "road",
        "roadside",
        "highway",
        "intersection",
        "lane",
        "pedestrian",
        "cyclist",
        "parking",
        "驾驶",
        "车辆",
        "交通",
        "道路",
        "路侧",
        "车道",
        "行人",
        "泊车",
    )
    technical_terms: tuple[str, ...] = (
        "bev",
        "bird's-eye",
        "bird’s-eye",
        "occupancy",
        "3d object detection",
        "3d detection",
        "sensor fusion",
        "multi-sensor",
        "multimodal fusion",
        "lidar",
        "point cloud",
        "4d radar",
        "radar",
        "trajectory prediction",
        "motion prediction",
        "motion planning",
        "path planning",
        "lane detection",
        "hd map",
        "visual localization",
        "monocular depth",
        "depth estimation",
        "vision-language-action",
        "driving vla",
        "world model",
        "gaussian splatting",
        "v2x",
        "vehicle-to-everything",
        "cooperative perception",
        "sim-to-real",
        "corner case",
        "anomaly detection",
        "场景生成",
        "轨迹预测",
        "运动规划",
        "点云",
        "深度估计",
        "占用预测",
        "多传感器融合",
    )
    ad_specific_terms: tuple[str, ...] = (
        "bev",
        "occupancy",
        "3d object detection",
        "sensor fusion",
        "camera-lidar",
        "camera-radar",
        "4d radar",
        "hd map",
        "trajectory prediction",
        "motion planning",
        "lane detection",
        "driving vla",
        "autonomous vehicle localization",
        "traffic object",
        "scene completion",
        "驾驶感知",
        "占用预测",
        "车道检测",
    )
    broad_signal_terms: tuple[str, ...] = (
        "bev",
        "occupancy",
        "3d object detection",
        "sensor fusion",
        "camera-lidar",
        "camera-radar",
        "4d radar",
        "hd map",
        "lane detection",
        "autonomous vehicle localization",
        "traffic object",
        "占用预测",
        "车道检测",
    )
    scene_terms: tuple[str, ...] = (
        "scene",
        "perception",
        "detection",
        "localization",
        "mapping",
        "tracking",
        "traffic",
        "road",
        "lane",
        "场景",
        "感知",
        "检测",
        "定位",
    )
    excluded_terms: tuple[str, ...] = (
        "medical",
        "healthcare",
        "diagnosis",
        "surgical",
        "pathology",
        "agriculture",
        "crop",
        "satellite",
        "remote sensing",
        "underwater",
        "uav",
        "drone",
        "aerial vehicle",
        "robot manipulation",
        "robot",
        "robotic",
        "grasping",
        "rail",
        "train condition",
        "humanoid",
        "embodied manipulation",
        "industrial anomaly",
        "microscopy",
        "beamforming",
        "talking head",
        "mobile gui",
        "economic agent",
        "wireless sensing",
        "uuv",
        "oil field",
        "volve field",
        "医学",
        "医疗",
        "诊断",
        "农业",
        "卫星",
        "遥感",
        "无人机",
        "铁路",
        "显微镜",
        "人形机器人",
    )
    hard_excluded_title_terms: tuple[str, ...] = (
        "medical",
        "healthcare",
        "diagnosis",
        "surgical",
        "pathology",
        "microscopy",
        "microscope",
        "barometric",
        "liver",
        "tumor",
        "mri",
        "robot manipulation",
        "robotic manipulation",
        "dexterous manipulation",
        "industrial dexterity",
        "liquid handling",
        "social robot",
        "robotic guide dog",
        "collaborative robotics",
        "social navigation",
        "chemical self-driving laboratory",
        "chemical self-driving laboratories",
        "robotic failure analysis",
        "trustworthy agentic ai",
        "industrial anomaly",
        "underwater",
        "uuv",
        "railway",
        "rail inspection",
        "train condition",
        "air traffic",
        "vessel",
        "maritime",
        "ship detection",
        "low-altitude",
        "aerial-ground",
        "high-speed flight",
        "uav-assisted",
        "tilt-rotor uav",
        "household",
        "food image",
        "cooking",
        "kitchen",
        "network traffic anomaly",
        "human motion reconstruction",
        "human-object-interaction",
        "embodied intelligence",
        "tire pattern recognition",
        "vehicle damage assessment",
        "sports to safety",
        "agriculture",
        "remote sensing",
        "医学",
        "医疗",
        "诊断",
        "显微镜",
        "肿瘤",
        "机器人操作",
        "工业异常",
        "水下",
        "铁路",
        "空中交通",
        "船舶",
        "家庭",
        "食品",
        "烹饪",
        "农业",
        "遥感",
    )
    title_specific_terms: tuple[str, ...] = (
        "4d radar",
        "camera-lidar",
        "camera-radar",
        "hd map",
        "lane detection",
        "driving vla",
        "vehicle-to-everything",
        "v2x",
        "roadside perception",
        "roadside 3d detection",
        "自动驾驶定位",
        "车道检测",
        "路侧感知",
    )

    tag_terms: dict[str, tuple[str, ...]] | None = None

    def __post_init__(self) -> None:
        self.tag_terms = {
            "端到端驾驶": ("end-to-end", "driving policy", "planning token", "端到端"),
            "VLM/VLA": ("vision-language", "vlm", "vla", "language-action", "多模态大模型"),
            "世界模型/生成": (
                "world model", "world action", "scene generation", "diffusion", "生成"
            ),
            "预测/规划": ("trajectory", "motion prediction", "planning", "planner", "轨迹", "规划"),
            "BEV/Occupancy": ("bev", "bird's-eye", "bird’s-eye", "occupancy", "占用"),
            "多传感器融合": (
                "sensor fusion", "multi-sensor", "camera-lidar", "camera-radar", "融合"
            ),
            "3D 检测": ("3d object detection", "3d detection", "3d visual grounding", "三维检测"),
            "LiDAR/点云": ("lidar", "point cloud", "lio", "点云", "激光雷达"),
            "Radar": ("radar", "mmwave", "毫米波雷达"),
            "地图/定位": ("hd map", "mapping", "localization", "slam", "地图", "定位"),
            "仿真/数据": ("dataset", "benchmark", "simulation", "sim-to-real", "数据集", "仿真"),
            "安全/异常": (
                "safety", "anomaly", "corner case", "out-of-distribution", "安全", "异常"
            ),
            "协同/V2X": ("v2x", "cooperative", "vehicle-to-everything", "协同"),
            "深度/几何": (
                "depth", "geometry", "reconstruction", "gaussian", "深度", "几何", "重建"
            ),
            "感知": ("perception", "segmentation", "detection", "tracking", "感知", "分割", "检测"),
        }

    def evaluate(self, paper: Paper) -> RelevanceResult:
        text = _normalized_text(paper)
        title_text = " ".join([paper.title, paper.title_zh]).casefold()
        explicit = _matches(text, self.explicit_terms)
        datasets = _matches(text, self.dataset_terms)
        contexts = _matches(text, self.context_terms)
        technical = _matches(text, self.technical_terms)
        ad_specific = _matches(text, self.ad_specific_terms)
        excluded = _matches(text, self.excluded_terms)
        title_excluded = _matches(title_text, self.hard_excluded_title_terms)
        title_specific = _matches(title_text, self.title_specific_terms)
        strong_road_context = [
            term
            for term in contexts
            if term
            not in {"autonomous", "driving", "vehicle", "car", "驾驶", "车辆"}
        ]

        score = min(
            100.0,
            len(explicit) * 28
            + len(datasets) * 20
            + len(contexts) * 5
            + len(technical) * 4,
        )
        weak_domain_evidence = bool(strong_road_context and technical)
        include = bool(explicit or datasets or title_specific)
        if weak_domain_evidence and score >= self.minimum_weak_score:
            include = True
        if title_excluded:
            include = False
            score = max(0.0, score - 30)
        elif excluded and not explicit and not datasets and not strong_road_context:
            include = False
            score = max(0.0, score - len(excluded) * 15)

        reasons: list[str] = []
        if explicit:
            reasons.append("明确的自动驾驶上下文")
        if datasets:
            reasons.append("使用自动驾驶数据集或仿真环境")
        if contexts and technical:
            reasons.append("驾驶场景与技术任务共同命中")
        if title_specific and not (explicit or datasets):
            reasons.append("标题命中自动驾驶专用技术")
        if weak_domain_evidence and score >= self.minimum_weak_score:
            reasons.append("道路场景与多个技术信号共同命中")
        if title_excluded:
            reasons.append("标题明确属于非道路驾驶领域")
        if excluded and not include:
            reasons.append("非自动驾驶领域排除词占主导")

        matched = list(
            dict.fromkeys(
                [
                    *explicit,
                    *datasets,
                    *contexts,
                    *technical,
                    *ad_specific,
                    *title_specific,
                    *excluded,
                    *title_excluded,
                ]
            )
        )
        return RelevanceResult(
            include=include,
            score=round(score, 2),
            matched_terms=matched,
            reasons=reasons,
        )

    def assign_tags(self, paper: Paper) -> TagAssignment:
        text = _normalized_text(paper)
        scored: list[tuple[int, int, str]] = []
        for order, tag in enumerate(self.tags):
            terms = (self.tag_terms or {}).get(tag, ())
            score = sum(1 for term in terms if term.casefold() in text)
            if score:
                scored.append((score, -order, tag))
        scored.sort(reverse=True)
        ordered = [tag for _, _, tag in scored]
        if not ordered:
            ordered = ["感知"]
        return TagAssignment(primary=ordered[0], secondary=ordered[1:3]).normalized()


plugin = AutonomousDrivingPlugin()
