#!/usr/bin/env python3
"""
gis_data/(sig_26, emd_26), pop_data/(인구통계...xlsx), geo/school_locations_source.json
을 읽어 geo/geo_data.json(강원 지역만 남긴 경량 지도/인구 데이터)을 생성한다.

필요 패키지: pyshp(shapefile), shapely, pyproj, openpyxl
    pip3 install pyshp shapely pyproj openpyxl
"""
import json
import sys
import unicodedata
from pathlib import Path

import shapefile
import shapely.geometry as geom
from shapely.geometry import shape as shapely_shape
from pyproj import Transformer
import openpyxl

ROOT = Path(__file__).resolve().parent.parent
GIS_DIR = ROOT / "gis_data"
POP_DIR = ROOT / "pop_data"
GEO_DIR = ROOT / "geo"
OUT_FILE = GEO_DIR / "geo_data.json"
SCHOOL_SRC_FILE = GEO_DIR / "school_locations_source.json"

SIG_TOLERANCE_M = 40      # 시군 경계 단순화 허용오차(m)
EMD_TOLERANCE_M = 12      # 읍면동 경계 단순화 허용오차(m)
SIG_MAP_W = 900           # 전체 강원 지도 SVG 너비 기준(px 단위 좌표계)
EMD_MAP_W = 700           # 시군별 드릴다운 지도 SVG 너비 기준
PAD = 12

# NEIS(data.json)와 공공데이터포털 표준데이터 사이 학교명 표기가 다른 경우 (개교/개명 등)
# key: 표준데이터 학교명 -> value: data.json 학교명
NAME_ALIASES = {
    "원주의료고등학교": "한국의료마이스터고등학교",
    "김화공업고등학교": "한국국방과학고등학교",
}

LEVEL_MAP = {"초등학교": "초", "중학교": "중", "고등학교": "고"}


def load_shapes(path, code_field_index, code_prefix):
    sf = shapefile.Reader(str(path), encoding="cp949")
    fields = [f[0] for f in sf.fields[1:]]  # skip DeletionFlag
    out = []
    for sr in sf.iterShapeRecords():
        rec = sr.record
        code = str(rec[code_field_index])
        if not code.startswith(code_prefix):
            continue
        try:
            g = shapely_shape(sr.shape.__geo_interface__)
        except Exception as e:
            print(f"  ! shape parse fail ({code}): {e}", file=sys.stderr)
            continue
        if not g.is_valid:
            g = g.buffer(0)
        out.append((code, rec, g))
    return out, fields


def rings_of(g):
    """Polygon/MultiPolygon -> list of rings (list of (x,y) tuples), exterior first per polygon."""
    polys = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
    rings = []
    for p in polys:
        if p.is_empty:
            continue
        rings.append(list(p.exterior.coords))
        for interior in p.interiors:
            rings.append(list(interior.coords))
    return rings


def make_transform(bbox, target_w, pad=PAD):
    minx, miny, maxx, maxy = bbox
    w = maxx - minx
    h = maxy - miny
    scale = (target_w - 2 * pad) / w if w else 1.0
    out_h = h * scale + 2 * pad
    return {"minX": minx, "maxY": maxy, "scale": scale, "pad": pad}, target_w, out_h


def to_svg(x, y, t):
    return (x - t["minX"]) * t["scale"] + t["pad"], (t["maxY"] - y) * t["scale"] + t["pad"]


def path_d(g, t):
    parts = []
    for ring in rings_of(g):
        pts = [to_svg(x, y, t) for x, y in ring]
        d = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in pts) + " Z"
        parts.append(d)
    return " ".join(parts)


def build_sig():
    print("시군 경계 처리 중...")
    shapes, fields = load_shapes(GIS_DIR / "sig_26" / "sig", 0, "51")
    print(f"  강원 시군 {len(shapes)}건")
    bbox = None
    features_raw = []
    for code, rec, g in shapes:
        name = rec[2]
        area_km2 = g.area / 1_000_000
        simp = g.simplify(SIG_TOLERANCE_M, preserve_topology=True)
        b = simp.bounds
        bbox = b if bbox is None else (
            min(bbox[0], b[0]), min(bbox[1], b[1]), max(bbox[2], b[2]), max(bbox[3], b[3])
        )
        features_raw.append((code, name, simp, area_km2, g.centroid))

    t, w, h = make_transform(bbox, SIG_MAP_W)
    features = []
    centroids = {}
    for code, name, simp, area_km2, centroid in features_raw:
        cx, cy = to_svg(centroid.x, centroid.y, t)
        features.append({
            "code": code, "name": name, "d": path_d(simp, t), "area_km2": round(area_km2, 3),
            "cx": round(cx, 1), "cy": round(cy, 1),
        })
        centroids[code] = (centroid.x, centroid.y)

    return {
        "viewBox": f"0 0 {w:.1f} {h:.1f}",
        "transform": t,
        "features": features,
    }, centroids


def build_emd():
    print("읍면동 경계 처리 중...")
    shapes, fields = load_shapes(GIS_DIR / "emd_26" / "emd", 0, "51")
    print(f"  강원 읍면동 {len(shapes)}건")
    groups = {}
    for code, rec, g in shapes:
        sig_code = code[:5]
        groups.setdefault(sig_code, []).append((code, rec[2], g))

    out = {}
    for sig_code, members in groups.items():
        bbox = None
        simplified = []
        for code, name, g in members:
            simp = g.simplify(EMD_TOLERANCE_M, preserve_topology=True)
            b = simp.bounds
            bbox = b if bbox is None else (
                min(bbox[0], b[0]), min(bbox[1], b[1]), max(bbox[2], b[2]), max(bbox[3], b[3])
            )
            simplified.append((code, name, simp))
        t, w, h = make_transform(bbox, EMD_MAP_W)
        features = []
        for c, n, g in simplified:
            cx, cy = to_svg(g.centroid.x, g.centroid.y, t)
            features.append({"code": c, "name": n, "d": path_d(g, t), "cx": round(cx, 1), "cy": round(cy, 1)})
        out[sig_code] = {"viewBox": f"0 0 {w:.1f} {h:.1f}", "transform": t, "features": features}
    return out


def build_schools(sig_centroids, sig_features):
    print("학교 좌표 투영 중...")
    schools_src = json.loads(SCHOOL_SRC_FILE.read_text(encoding="utf-8"))
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)

    # data.json의 (name -> region) 매핑을 만들어 소속 시군을 확인
    data_json = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
    name_to_region = {}
    name_level_seen = set()
    for rec in data_json:
        key = (rec["name"], rec["level"])
        name_to_region[key] = rec["region"]
        name_level_seen.add(key)

    name_to_code_by_region = {r["name"]: r["code"] for r in sig_features}

    out = []
    unmatched = []
    for s in schools_src:
        level = LEVEL_MAP.get(s["level_raw"])
        if not level:
            continue
        name = NAME_ALIASES.get(s["name"], s["name"])
        key = (name, level)
        region = name_to_region.get(key)
        x_m, y_m = transformer.transform(s["lon"], s["lat"])
        if region is None:
            unmatched.append(s["name"])
        out.append({
<<<<<<< HEAD
            "name": name, "level": level, "region": region,
=======
<<<<<<< Updated upstream
            "name": s["name"], "level": level, "region": region,
=======
<<<<<<< HEAD
            "name": name, "level": level, "region": region,
=======
            "name": s["name"], "level": level, "region": region,
>>>>>>> 62520d9cbc28eb03861cd0f9f6be7d6edf0a1236
>>>>>>> Stashed changes
>>>>>>> ceb51a0627671727e9ed315791fc1eeaf1a040b8
            "x_m": round(x_m, 1), "y_m": round(y_m, 1),
        })

    if unmatched:
        print(f"  ! data.json과 이름 매칭 안 된 학교 {len(unmatched)}건 (지역 정보 없이 저장): {unmatched}")
    print(f"  총 {len(out)}건")
    return out


AGE_YOUTH = range(0, 15)      # 0~14
AGE_ELDERLY_START = 65        # 65세 이상


def build_population():
    print("인구 데이터 처리 중...")
    files = [p for p in POP_DIR.glob("*.xlsx") if unicodedata.normalize("NFC", p.name).startswith("인구통계")]
    if not files:
        raise SystemExit(f"{POP_DIR}에 인구통계 xlsx 파일이 없습니다.")
    f = sorted(files)[0]
    wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
    ws = wb["연령별인구현황"]
    rows = list(ws.iter_rows(values_only=True))
    header_idx = next(i for i, r in enumerate(rows) if r[0] == "행정기관코드")
    header = rows[header_idx]
    age_cols = {}
    for i, col in enumerate(header):
        if isinstance(col, str) and col.endswith("세"):
            age_cols[i] = int(col[:-1])
        elif col == "100세 이상":
            age_cols[i] = 100

    def num(v):
        if v is None:
            return 0
        if isinstance(v, str):
            v = v.replace(",", "").strip()
            if not v:
                return 0
        return int(v)

    out = {}
    for r in rows[header_idx + 1:]:
        if not r[0] or not str(r[0]).strip().isdigit():
            continue
        code = str(r[0])
        raw_name = (r[1] or "").strip()
        year = r[2]
        if not isinstance(year, int):
            continue
        if not (code.startswith("51") or code.startswith("42")):
            continue
        sig_name = raw_name.split()[-1] if raw_name.split() else raw_name
        if sig_name in ("강원특별자치도", "강원도"):
            continue  # 전체 합계 행 제외 (시군만 사용)

        youth = sum(num(r[i]) for i, age in age_cols.items() if age <= 14)
        elderly = sum(num(r[i]) for i, age in age_cols.items() if age >= 65)
        total = num(r[3])
        working = total - youth - elderly

        def pct(n):
            return round(n / total * 100, 1) if total else 0

        out.setdefault(str(year), {})[sig_name] = {
            "name": sig_name,
            "total": total,
            "youth": {"count": youth, "pct": pct(youth)},
            "working": {"count": working, "pct": pct(working)},
            "elderly": {"count": elderly, "pct": pct(elderly)},
        }
    years = sorted(out.keys())
    print(f"  연도: {years}, 시군 수(최신연도): {len(out[years[-1]]) if years else 0}")
    return out


def main():
    GEO_DIR.mkdir(exist_ok=True)
    sig, sig_centroids = build_sig()
    emd_by_sig = build_emd()
    schools = build_schools(sig_centroids, sig["features"])
    population = build_population()

    # population은 시군 '이름'으로 키가 잡혀 있으므로 sig code -> name 매핑을 붙여서
    # 런타임에서 sig code 로도 조회할 수 있도록 name 기준 population을 그대로 둔다.
    # (sig.features[i].name 과 population[year][name] 이 매칭됨)

    data = {
        "sig": sig,
        "emdBySig": emd_by_sig,
        "schools": schools,
        "population": population,
    }
    OUT_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    size_mb = OUT_FILE.stat().st_size / 1_000_000
    print(f"\n완료: {OUT_FILE} ({size_mb:.2f} MB)")
    print(f"  시군 {len(sig['features'])}개, 읍면동 그룹 {len(emd_by_sig)}개"
          f" (읍면동 총 {sum(len(v['features']) for v in emd_by_sig.values())}개)")
    print(f"  학교 {len(schools)}건, 인구 연도 {sorted(population.keys())}")


if __name__ == "__main__":
    main()
