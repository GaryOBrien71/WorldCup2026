
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
except Exception:  # pragma: no cover - app still works without plotly
    px = None

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data" if (BASE_DIR / "data").exists() else BASE_DIR
ASSET_DIR = BASE_DIR / "assets" if (BASE_DIR / "assets").exists() else BASE_DIR

st.set_page_config(
    page_title="World Cup 2026 Predictor",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)


def asset_uri(name: str) -> str:
    data = (ASSET_DIR / name).read_bytes()
    mime = "image/svg+xml" if name.endswith(".svg") else "image/png"
    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


BADGE_URI = asset_uri("worldcup_badge.svg")
STADIUM_URI = asset_uri("stadium_header.svg")
TROPHY_URI = asset_uri("trophy.svg")

st.markdown(
    f"""
    <style>
      :root {{ --navy:#06162f; --blue:#0f3b69; --green:#10b981; --gold:#facc15; --red:#ef4444; }}
      .stApp {{ background: linear-gradient(180deg, #f8fafc 0%, #eef6ff 44%, #f6fff9 100%); }}
      [data-testid="stSidebar"] {{ background: linear-gradient(180deg, #06162f 0%, #0f3b69 58%, #064e3b 100%); }}
      [data-testid="stSidebar"] * {{ color: #f8fafc; }}
      .hero {{
        background-image: linear-gradient(90deg, rgba(6,22,47,.92), rgba(15,59,105,.74), rgba(6,78,59,.82)), url('{STADIUM_URI}');
        background-size: cover; background-position: center; border-radius: 28px; padding: 26px 28px;
        box-shadow: 0 14px 42px rgba(2,8,23,.22); margin-bottom: 18px; border: 1px solid rgba(255,255,255,.18);
      }}
      .hero-grid {{ display: grid; grid-template-columns: minmax(230px, 360px) 1fr; gap: 26px; align-items: center; }}
      .hero img {{ width: 100%; max-width: 360px; border-radius: 22px; box-shadow: 0 16px 38px rgba(0,0,0,.25); }}
      .hero h1 {{ color: #ffffff; font-size: clamp(2.0rem, 4vw, 4.1rem); line-height: 1; margin: 0 0 8px 0; font-weight: 900; letter-spacing: -.04em; }}
      .hero p {{ color: #dbeafe; font-size: 1.1rem; margin: 0; max-width: 850px; }}
      .pill-row {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:18px; }}
      .pill {{ color:#052e5c; background:#facc15; border-radius:999px; padding:7px 13px; font-weight:800; box-shadow:0 4px 16px rgba(250,204,21,.2); }}
      .card {{ background: rgba(255,255,255,.88); border:1px solid rgba(15,59,105,.12); border-radius: 22px; padding: 18px; box-shadow: 0 8px 28px rgba(15,59,105,.08); }}
      .team-chip {{ display:inline-flex; align-items:center; gap:8px; background:#eff6ff; border:1px solid #bfdbfe; border-radius:999px; padding:4px 10px; font-weight:750; margin:2px; }}
      .match-card {{ border-radius:18px; border:1px solid #dbeafe; padding:14px; background:#ffffff; margin-bottom:11px; box-shadow:0 5px 18px rgba(15,59,105,.07); }}
      .stage-title {{ color:#06162f; font-weight:900; border-left:6px solid #10b981; padding-left:12px; margin-top:18px; }}
      .small-muted {{ color:#64748b; font-size:.88rem; }}
      .winner {{ background:#dcfce7; border-color:#86efac; }}
      .loser {{ opacity:.72; }}
      div[data-testid="stMetricValue"] {{ color:#052e5c; font-weight:900; }}
      @media (max-width: 780px) {{ .hero-grid {{ grid-template-columns: 1fr; }} .hero img {{ max-width: 250px; }} }}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_data() -> Tuple[pd.DataFrame, pd.DataFrame, List[str]]:
    fixtures = pd.read_csv(DATA_DIR / "fixtures.csv")
    groups = pd.read_csv(DATA_DIR / "groups.csv")
    players = json.loads((DATA_DIR / "players.json").read_text(encoding="utf-8"))
    fixtures["date"] = pd.to_datetime(fixtures["date"], errors="coerce").dt.date
    fixtures["display_date"] = fixtures["date"].apply(lambda d: d.strftime("%d %b %Y") if pd.notna(d) else "")
    return fixtures, groups, players


fixtures_df, groups_df, default_players = load_data()
TEAM_FLAG = dict(zip(groups_df["team"], groups_df["flag"]))
TEAM_CODE = dict(zip(groups_df["team"], groups_df["flag_code"].fillna("")))
TEAM_GROUP = dict(zip(groups_df["team"], groups_df["group"]))


def init_state() -> None:
    st.session_state.setdefault("results", {})
    st.session_state.setdefault("predictions", {p: {} for p in default_players})
    st.session_state.setdefault("players", default_players[:])
    st.session_state.setdefault("show_online_flags", False)
    st.session_state.setdefault("knockout", {})


init_state()


def flag_for(team: str, image: bool = False) -> str:
    emoji = TEAM_FLAG.get(team, "🏳️")
    code = TEAM_CODE.get(team, "")
    if image and isinstance(code, str) and len(code) == 2:
        return f'<img src="https://flagcdn.com/w40/{code.lower()}.png" width="24" style="border-radius:3px; vertical-align:-5px; margin-right:6px;">'
    return emoji + " "


def team_html(team: str, strong: bool = False) -> str:
    name = f"<strong>{team}</strong>" if strong else team
    return f"<span class='team-chip'>{flag_for(team, st.session_state.show_online_flags)}{name}</span>"


def result_key(match_id: str) -> str:
    return str(match_id)


def get_result(match_id: str) -> Optional[Tuple[int, int]]:
    raw = st.session_state.results.get(result_key(match_id))
    if not raw:
        return None
    try:
        return int(raw["home_goals"]), int(raw["away_goals"])
    except Exception:
        return None


def set_result(match_id: str, home_goals, away_goals) -> None:
    key = result_key(match_id)
    if pd.isna(home_goals) or pd.isna(away_goals) or home_goals is None or away_goals is None:
        st.session_state.results.pop(key, None)
        return
    st.session_state.results[key] = {"home_goals": int(home_goals), "away_goals": int(away_goals)}


def outcome(h: int, a: int) -> str:
    if h > a:
        return "H"
    if h < a:
        return "A"
    return "D"


def fixture_table_with_results(rows: pd.DataFrame) -> pd.DataFrame:
    df = rows.copy()
    scores = df["match_id"].map(get_result)
    df["home_goals"] = [s[0] if s else pd.NA for s in scores]
    df["away_goals"] = [s[1] if s else pd.NA for s in scores]
    df["home_flag"] = df["home"].map(lambda t: TEAM_FLAG.get(t, "") if t else "")
    df["away_flag"] = df["away"].map(lambda t: TEAM_FLAG.get(t, "") if t else "")
    return df


def calculate_standings(fixtures: pd.DataFrame, groups: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    tables: Dict[str, List[dict]] = {}
    for _, row in groups.iterrows():
        g = str(row["group"])
        tables.setdefault(g, []).append({
            "Team": row["team"], "Flag": row["flag"], "P": 0, "W": 0, "D": 0, "L": 0,
            "GF": 0, "GA": 0, "GD": 0, "Pts": 0,
        })
    lookup = {(g, rec["Team"]): rec for g, rows in tables.items() for rec in rows}
    for _, fx in fixtures[fixtures["stage"] == "Group Stage"].iterrows():
        res = get_result(fx["match_id"])
        if res is None:
            continue
        h, a = res
        g = str(fx["group"])
        home = fx["home"]
        away = fx["away"]
        if not home or not away or (g, home) not in lookup or (g, away) not in lookup:
            continue
        rh = lookup[(g, home)]
        ra = lookup[(g, away)]
        rh["P"] += 1; ra["P"] += 1
        rh["GF"] += h; rh["GA"] += a
        ra["GF"] += a; ra["GA"] += h
        if h > a:
            rh["W"] += 1; rh["Pts"] += 3; ra["L"] += 1
        elif h < a:
            ra["W"] += 1; ra["Pts"] += 3; rh["L"] += 1
        else:
            rh["D"] += 1; ra["D"] += 1; rh["Pts"] += 1; ra["Pts"] += 1
    out: Dict[str, pd.DataFrame] = {}
    for g, rows in tables.items():
        df = pd.DataFrame(rows)
        df["GD"] = df["GF"] - df["GA"]
        df = df.sort_values(["Pts", "GD", "GF", "Team"], ascending=[False, False, False, True]).reset_index(drop=True)
        df.insert(0, "Rank", range(1, len(df) + 1))
        out[g] = df
    return out


def standings_all() -> pd.DataFrame:
    frames = []
    for group, table in calculate_standings(fixtures_df, groups_df).items():
        temp = table.copy()
        temp.insert(1, "Group", group)
        frames.append(temp)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def qualifiers_table() -> pd.DataFrame:
    all_standings = standings_all()
    if all_standings.empty:
        return all_standings
    auto = all_standings[all_standings["Rank"].isin([1, 2])].copy()
    thirds = all_standings[all_standings["Rank"] == 3].copy()
    thirds = thirds.sort_values(["Pts", "GD", "GF", "Team"], ascending=[False, False, False, True]).head(8)
    q = pd.concat([auto, thirds], ignore_index=True)
    q = q.sort_values(["Pts", "GD", "GF", "Rank", "Team"], ascending=[False, False, False, True, True]).reset_index(drop=True)
    q.insert(0, "Seed", range(1, len(q) + 1))
    return q


BRACKET_PAIRINGS = [(1,32),(16,17),(8,25),(9,24),(4,29),(13,20),(5,28),(12,21),(2,31),(15,18),(7,26),(10,23),(3,30),(14,19),(6,27),(11,22)]


def seed_to_team(q: pd.DataFrame, seed: int) -> str:
    rows = q[q["Seed"] == seed]
    if rows.empty:
        return f"Seed {seed}"
    row = rows.iloc[0]
    return str(row["Team"])


def match_result_from_knockout(stage: str, i: int) -> Optional[Tuple[int, int, Optional[int], Optional[int]]]:
    return st.session_state.knockout.get(f"{stage}_{i}")


def choose_winner(home: str, away: str, result: Optional[dict]) -> Optional[str]:
    if not result:
        return None
    hg, ag = int(result.get("home_goals", 0)), int(result.get("away_goals", 0))
    if hg > ag:
        return home
    if ag > hg:
        return away
    hp = result.get("home_pens")
    ap = result.get("away_pens")
    if hp is None or ap is None:
        return None
    if int(hp) > int(ap):
        return home
    if int(ap) > int(hp):
        return away
    return None


def choose_loser(home: str, away: str, result: Optional[dict]) -> Optional[str]:
    w = choose_winner(home, away, result)
    if w is None:
        return None
    return away if w == home else home


def pair_next(winners: List[Optional[str]], placeholder_prefix: str) -> List[Tuple[str, str]]:
    pairs = []
    for i in range(0, len(winners), 2):
        h = winners[i] if i < len(winners) and winners[i] else f"Winner {placeholder_prefix} {i+1}"
        a = winners[i+1] if i+1 < len(winners) and winners[i+1] else f"Winner {placeholder_prefix} {i+2}"
        pairs.append((h, a))
    return pairs


def render_match_card(stage: str, i: int, home: str, away: str) -> Optional[str]:
    key = f"{stage}_{i}"
    existing = st.session_state.knockout.get(key, {})
    played_default = bool(existing)
    with st.container(border=True):
        st.markdown(f"**{stage.replace('_', ' ')} #{i+1}**")
        st.markdown(f"{team_html(home, True)} <span style='font-weight:900;color:#64748b'>v</span> {team_html(away, True)}", unsafe_allow_html=True)
        played = st.checkbox("Played", value=played_default, key=f"played_{key}")
        c1, c2, c3 = st.columns([1, .25, 1])
        with c1:
            hg = st.number_input(home, min_value=0, max_value=30, value=int(existing.get("home_goals", 0)), step=1, key=f"hg_{key}")
        with c2:
            st.markdown("<div style='text-align:center;font-size:1.7rem;font-weight:900;margin-top:22px;'>–</div>", unsafe_allow_html=True)
        with c3:
            ag = st.number_input(away, min_value=0, max_value=30, value=int(existing.get("away_goals", 0)), step=1, key=f"ag_{key}")
        hp = ap = None
        if played and hg == ag:
            p1, p2 = st.columns(2)
            with p1:
                hp = st.number_input(f"{home} penalties", min_value=0, max_value=20, value=int(existing.get("home_pens", 0)), step=1, key=f"hp_{key}")
            with p2:
                ap = st.number_input(f"{away} penalties", min_value=0, max_value=20, value=int(existing.get("away_pens", 0)), step=1, key=f"ap_{key}")
        if played:
            rec = {"home_goals": int(hg), "away_goals": int(ag), "home_pens": int(hp) if hp is not None else None, "away_pens": int(ap) if ap is not None else None}
            st.session_state.knockout[key] = rec
            winner = choose_winner(home, away, rec)
            if winner:
                st.success(f"Winner: {flag_for(winner)}{winner}")
            else:
                st.warning("Add a penalty winner for a drawn knockout match.")
            return winner
        else:
            st.session_state.knockout.pop(key, None)
            return None


def render_hero() -> None:
    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-grid">
            <img src="{BADGE_URI}" alt="World Cup 2026 Predictor badge">
            <div>
              <h1>World Cup 2026 Predictor</h1>
              <p>Converted from the uploaded Excel workbook into a Streamlit app with interactive results entry, group tables, player predictions, provisional knockout bracket, flags, colour, and original tournament-style graphics.</p>
              <div class="pill-row">
                <span class="pill">⚽ 48 teams</span><span class="pill">🏆 12 groups</span><span class="pill">📊 live tables</span><span class="pill">👨‍👩‍👧‍👦 family leaderboard</span>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_controls() -> str:
    st.sidebar.image(str(ASSET_DIR / "trophy.svg"), use_container_width=True)
    page = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Enter Results", "Group Tables", "Player Predictions", "Knockout Bracket", "Fixtures"],
        index=0,
    )
    st.sidebar.divider()
    st.session_state.show_online_flags = st.sidebar.toggle("Use online flag images", value=st.session_state.show_online_flags, help="Uses FlagCDN for ISO country flags where available; emoji flags are always available.")
    with st.sidebar.expander("Players", expanded=False):
        player_text = st.text_area("One player per line", value="\n".join(st.session_state.players), height=120)
        if st.button("Update players"):
            players = [p.strip() for p in player_text.splitlines() if p.strip()]
            if players:
                st.session_state.players = players
                for p in players:
                    st.session_state.predictions.setdefault(p, {})
                st.success("Players updated.")
    with st.sidebar.expander("Save / load state", expanded=False):
        state = {
            "results": st.session_state.results,
            "predictions": st.session_state.predictions,
            "players": st.session_state.players,
            "knockout": st.session_state.knockout,
        }
        st.download_button("Download app state JSON", data=json.dumps(state, indent=2), file_name="worldcup2026_predictor_state.json", mime="application/json")
        upload = st.file_uploader("Restore state JSON", type=["json"])
        if upload is not None:
            try:
                incoming = json.loads(upload.read().decode("utf-8"))
                st.session_state.results = incoming.get("results", {})
                st.session_state.predictions = incoming.get("predictions", {})
                st.session_state.players = incoming.get("players", st.session_state.players)
                st.session_state.knockout = incoming.get("knockout", {})
                st.success("State restored. Change page or rerun if needed.")
            except Exception as exc:
                st.error(f"Could not restore that JSON file: {exc}")
        if st.button("Reset all scores and predictions"):
            st.session_state.results = {}
            st.session_state.predictions = {p: {} for p in st.session_state.players}
            st.session_state.knockout = {}
            st.success("Reset complete.")
    st.sidebar.caption("Fan-made app graphics are included locally. No official FIFA logo is bundled.")
    return page


def render_dashboard() -> None:
    group_matches = fixtures_df[fixtures_df["stage"] == "Group Stage"]
    played = sum(1 for mid in group_matches["match_id"] if get_result(mid) is not None)
    total = len(group_matches)
    q = qualifiers_table()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Group matches played", f"{played}/{total}")
    c2.metric("Teams", str(groups_df["team"].nunique()))
    c3.metric("Groups", str(groups_df["group"].nunique()))
    c4.metric("Projected qualifiers", str(len(q)))
    left, right = st.columns([1.35, .9])
    with left:
        st.markdown("### Upcoming / unplayed fixtures")
        upcoming = fixture_table_with_results(group_matches).copy()
        upcoming = upcoming[upcoming["home_goals"].isna() | upcoming["away_goals"].isna()].head(12)
        if upcoming.empty:
            st.success("All group-stage fixtures have a result.")
        else:
            for _, row in upcoming.iterrows():
                st.markdown(f"<div class='match-card'><span class='small-muted'>{row['display_date']} • Group {row['group']} • {row['match_id']}</span><br>{team_html(row['home'], True)} <strong>v</strong> {team_html(row['away'], True)}</div>", unsafe_allow_html=True)
    with right:
        st.markdown("### Current top seeds")
        if not q.empty:
            top = q.head(10)[["Seed", "Flag", "Team", "Group", "Rank", "Pts", "GD"]]
            st.dataframe(top, use_container_width=True, hide_index=True)
        st.image(str(ASSET_DIR / "worldcup_badge.svg"), use_container_width=True)
    st.markdown("### Goals by match date")
    res_rows = []
    for _, row in group_matches.iterrows():
        res = get_result(row["match_id"])
        if res:
            res_rows.append({"Date": row["date"], "Goals": res[0] + res[1]})
    if res_rows:
        goals_df = pd.DataFrame(res_rows).groupby("Date", as_index=False)["Goals"].sum()
        if px:
            fig = px.bar(goals_df, x="Date", y="Goals", title="Total entered goals by date")
            fig.update_layout(height=360, margin=dict(l=10, r=10, t=52, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.bar_chart(goals_df.set_index("Date"))
    else:
        st.info("Enter some scores to populate the goals chart.")


def result_editor(page_title: str, data: pd.DataFrame) -> None:
    st.markdown(f"### {page_title}")
    df = fixture_table_with_results(data)
    if df.empty:
        st.info("No matches in this filter.")
        return
    editable = df[["match_id", "display_date", "round", "group", "home_flag", "home", "home_goals", "away_goals", "away", "away_flag"]].rename(columns={
        "display_date": "Date", "round": "Round", "group": "Group", "home_flag": "", "home": "Home", "home_goals": "Home goals", "away_goals": "Away goals", "away": "Away", "away_flag": " "
    })
    edited = st.data_editor(
        editable,
        use_container_width=True,
        hide_index=True,
        disabled=["match_id", "Date", "Round", "Group", "", "Home", "Away", " "],
        column_config={
            "Home goals": st.column_config.NumberColumn("Home goals", min_value=0, max_value=30, step=1, required=False),
            "Away goals": st.column_config.NumberColumn("Away goals", min_value=0, max_value=30, step=1, required=False),
        },
        key=f"editor_{page_title}",
    )
    if st.button("Save shown scores", type="primary"):
        for _, row in edited.iterrows():
            set_result(row["match_id"], row["Home goals"], row["Away goals"])
        st.success("Scores saved.")


def render_enter_results() -> None:
    st.markdown("## Enter Results")
    group_options = ["All"] + sorted([str(g) for g in fixtures_df[fixtures_df["stage"] == "Group Stage"]["group"].dropna().unique() if str(g)])
    col1, col2, col3 = st.columns(3)
    with col1:
        group = st.selectbox("Group", group_options)
    with col2:
        date_options = ["All"] + sorted(fixtures_df[fixtures_df["stage"] == "Group Stage"]["display_date"].dropna().unique().tolist())
        date = st.selectbox("Date", date_options)
    with col3:
        team_query = st.text_input("Filter by team")
    data = fixtures_df[fixtures_df["stage"] == "Group Stage"].copy()
    if group != "All":
        data = data[data["group"].astype(str) == group]
    if date != "All":
        data = data[data["display_date"] == date]
    if team_query.strip():
        q = team_query.strip().lower()
        data = data[data["home"].str.lower().str.contains(q, na=False) | data["away"].str.lower().str.contains(q, na=False)]
    result_editor("Group-stage score entry", data)


def render_group_tables() -> None:
    st.markdown("## Group Tables")
    tables = calculate_standings(fixtures_df, groups_df)
    group_names = sorted(tables.keys())
    selected = st.multiselect("Show groups", group_names, default=group_names)
    cols = st.columns(3)
    for idx, group in enumerate(selected):
        table = tables[group]
        view = table[["Rank", "Flag", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"]].copy()
        with cols[idx % 3]:
            st.markdown(f"<h3 class='stage-title'>Group {group}</h3>", unsafe_allow_html=True)
            st.dataframe(view, hide_index=True, use_container_width=True)
    st.markdown("## Best third-placed teams")
    all_rows = standings_all()
    thirds = all_rows[all_rows["Rank"] == 3].sort_values(["Pts", "GD", "GF", "Team"], ascending=[False, False, False, True])
    if not thirds.empty:
        thirds = thirds[["Flag", "Team", "Group", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"]].copy()
        thirds.insert(0, "Status", ["Qualifies" if i < 8 else "Out" for i in range(len(thirds))])
        st.dataframe(thirds, use_container_width=True, hide_index=True)


def score_prediction(actual: Optional[Tuple[int, int]], pred: Optional[Tuple[int, int]]) -> int:
    if actual is None or pred is None:
        return 0
    if actual == pred:
        return 3
    if outcome(*actual) == outcome(*pred):
        return 1
    return 0


def get_prediction(player: str, match_id: str) -> Optional[Tuple[int, int]]:
    raw = st.session_state.predictions.get(player, {}).get(str(match_id))
    if not raw:
        return None
    try:
        return int(raw["home_goals"]), int(raw["away_goals"])
    except Exception:
        return None


def set_prediction(player: str, match_id: str, home_goals, away_goals) -> None:
    st.session_state.predictions.setdefault(player, {})
    if pd.isna(home_goals) or pd.isna(away_goals) or home_goals is None or away_goals is None:
        st.session_state.predictions[player].pop(str(match_id), None)
    else:
        st.session_state.predictions[player][str(match_id)] = {"home_goals": int(home_goals), "away_goals": int(away_goals)}


def leaderboard() -> pd.DataFrame:
    rows = []
    group_matches = fixtures_df[fixtures_df["stage"] == "Group Stage"]
    for player in st.session_state.players:
        pts = exact = outcomes = predicted = 0
        for _, fx in group_matches.iterrows():
            actual = get_result(fx["match_id"])
            pred = get_prediction(player, fx["match_id"])
            if pred is not None:
                predicted += 1
            val = score_prediction(actual, pred)
            pts += val
            if actual is not None and pred is not None:
                if actual == pred:
                    exact += 1
                elif val == 1:
                    outcomes += 1
        rows.append({"Player": player, "Points": pts, "Exact scores": exact, "Correct outcomes": outcomes, "Predictions entered": predicted})
    return pd.DataFrame(rows).sort_values(["Points", "Exact scores", "Correct outcomes", "Player"], ascending=[False, False, False, True]).reset_index(drop=True)


def render_predictions() -> None:
    st.markdown("## Player Predictions")
    st.caption("Prediction scoring: 3 points for exact score, 1 point for correct outcome, 0 otherwise. Actual scores come from the Enter Results page.")
    board = leaderboard()
    st.markdown("### Leaderboard")
    st.dataframe(board, use_container_width=True, hide_index=True)
    if not board.empty and px:
        fig = px.bar(board, x="Player", y="Points", text="Points", title="Prediction leaderboard")
        fig.update_layout(height=340, margin=dict(l=10, r=10, t=52, b=10))
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("### Enter predictions")
    player = st.selectbox("Player", st.session_state.players)
    c1, c2, c3 = st.columns(3)
    with c1:
        group_options = ["All"] + sorted(fixtures_df[fixtures_df["stage"] == "Group Stage"]["group"].dropna().unique().tolist())
        group = st.selectbox("Group filter", group_options, key="pred_group")
    with c2:
        date_options = ["All"] + sorted(fixtures_df[fixtures_df["stage"] == "Group Stage"]["display_date"].dropna().unique().tolist())
        date = st.selectbox("Date filter", date_options, key="pred_date")
    with c3:
        team_query = st.text_input("Team filter", key="pred_team")
    data = fixtures_df[fixtures_df["stage"] == "Group Stage"].copy()
    if group != "All":
        data = data[data["group"] == group]
    if date != "All":
        data = data[data["display_date"] == date]
    if team_query.strip():
        q = team_query.strip().lower()
        data = data[data["home"].str.lower().str.contains(q, na=False) | data["away"].str.lower().str.contains(q, na=False)]
    if data.empty:
        st.info("No fixtures in this filter.")
        return
    rows = []
    for _, fx in data.iterrows():
        pred = get_prediction(player, fx["match_id"])
        actual = get_result(fx["match_id"])
        rows.append({
            "match_id": fx["match_id"], "Date": fx["display_date"], "Group": fx["group"], "Home": f"{TEAM_FLAG.get(fx['home'],'')} {fx['home']}",
            "Pred home": pred[0] if pred else pd.NA, "Pred away": pred[1] if pred else pd.NA,
            "Away": f"{TEAM_FLAG.get(fx['away'],'')} {fx['away']}",
            "Actual": "" if actual is None else f"{actual[0]}–{actual[1]}",
            "Points": score_prediction(actual, pred),
        })
    edit_df = pd.DataFrame(rows)
    edited = st.data_editor(
        edit_df,
        hide_index=True,
        use_container_width=True,
        disabled=["match_id", "Date", "Group", "Home", "Away", "Actual", "Points"],
        column_config={
            "Pred home": st.column_config.NumberColumn("Pred home", min_value=0, max_value=30, step=1),
            "Pred away": st.column_config.NumberColumn("Pred away", min_value=0, max_value=30, step=1),
        },
        key=f"pred_editor_{player}_{group}_{date}_{team_query}",
    )
    if st.button("Save shown predictions", type="primary"):
        for _, row in edited.iterrows():
            set_prediction(player, row["match_id"], row["Pred home"], row["Pred away"])
        st.success(f"Predictions saved for {player}.")


def render_knockout() -> None:
    st.markdown("## Knockout Bracket")
    st.info("The workbook supplied knockout dates but not the knockout team mapping. This app therefore creates a provisional 32-team bracket from the current group tables: all group winners/runners-up plus the eight best third-placed teams, seeded by points, goal difference, goals for, and group rank.")
    q = qualifiers_table()
    if q.empty:
        st.warning("No qualifying table available yet.")
        return
    st.markdown("### Projected qualifiers")
    q_view = q[["Seed", "Flag", "Team", "Group", "Rank", "P", "Pts", "GD", "GF"]]
    st.dataframe(q_view, use_container_width=True, hide_index=True)
    if len(q) < 32:
        st.warning("Fewer than 32 qualifiers could be calculated.")
        return
    r32_pairs = [(seed_to_team(q, a), seed_to_team(q, b)) for a, b in BRACKET_PAIRINGS]
    stages = []
    st.markdown("<h3 class='stage-title'>Round of 32</h3>", unsafe_allow_html=True)
    winners = []
    cols = st.columns(4)
    for i, pair in enumerate(r32_pairs):
        with cols[i % 4]:
            winners.append(render_match_card("R32", i, pair[0], pair[1]))
    r16_pairs = pair_next(winners, "R32")
    st.markdown("<h3 class='stage-title'>Round of 16</h3>", unsafe_allow_html=True)
    winners16 = []
    cols = st.columns(4)
    for i, pair in enumerate(r16_pairs):
        with cols[i % 4]:
            winners16.append(render_match_card("R16", i, pair[0], pair[1]))
    qf_pairs = pair_next(winners16, "R16")
    st.markdown("<h3 class='stage-title'>Quarter-finals</h3>", unsafe_allow_html=True)
    winners_qf = []
    cols = st.columns(4)
    for i, pair in enumerate(qf_pairs):
        with cols[i % 4]:
            winners_qf.append(render_match_card("QF", i, pair[0], pair[1]))
    sf_pairs = pair_next(winners_qf, "QF")
    st.markdown("<h3 class='stage-title'>Semi-finals</h3>", unsafe_allow_html=True)
    winners_sf = []
    losers_sf = []
    cols = st.columns(2)
    for i, pair in enumerate(sf_pairs):
        with cols[i % 2]:
            winners_sf.append(render_match_card("SF", i, pair[0], pair[1]))
            losers_sf.append(choose_loser(pair[0], pair[1], st.session_state.knockout.get(f"SF_{i}")))
    st.markdown("<h3 class='stage-title'>Finals Weekend</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        third_home = losers_sf[0] if len(losers_sf) > 0 and losers_sf[0] else "Loser SF 1"
        third_away = losers_sf[1] if len(losers_sf) > 1 and losers_sf[1] else "Loser SF 2"
        render_match_card("THIRD_PLACE", 0, third_home, third_away)
    with c2:
        final_home = winners_sf[0] if len(winners_sf) > 0 and winners_sf[0] else "Winner SF 1"
        final_away = winners_sf[1] if len(winners_sf) > 1 and winners_sf[1] else "Winner SF 2"
        champion = render_match_card("FINAL", 0, final_home, final_away)
        if champion:
            st.balloons()
            st.markdown(f"<div class='card' style='text-align:center;'><img src='{TROPHY_URI}' style='width:105px;'><h2>Champion: {flag_for(champion)}{champion}</h2></div>", unsafe_allow_html=True)


def render_fixtures() -> None:
    st.markdown("## Fixtures")
    stage = st.selectbox("Stage", ["All"] + sorted(fixtures_df["stage"].dropna().unique().tolist()))
    data = fixtures_df.copy()
    if stage != "All":
        data = data[data["stage"] == stage]
    data = fixture_table_with_results(data)
    data["Score"] = data.apply(lambda r: "" if pd.isna(r["home_goals"]) or pd.isna(r["away_goals"]) else f"{int(r['home_goals'])}–{int(r['away_goals'])}", axis=1)
    view = data[["match_id", "display_date", "stage", "round", "group", "home_flag", "home", "Score", "away", "away_flag", "workbook_row"]].rename(columns={
        "match_id": "Match", "display_date": "Date", "stage": "Stage", "round": "Round", "group": "Group", "home_flag": "", "home": "Home", "away": "Away", "away_flag": " ", "workbook_row": "Workbook row"
    })
    st.dataframe(view, use_container_width=True, hide_index=True)
    st.download_button("Download fixtures/results CSV", data=view.to_csv(index=False).encode("utf-8"), file_name="worldcup2026_fixtures_results.csv", mime="text/csv")


def main() -> None:
    render_hero()
    page = sidebar_controls()
    if page == "Dashboard":
        render_dashboard()
    elif page == "Enter Results":
        render_enter_results()
    elif page == "Group Tables":
        render_group_tables()
    elif page == "Player Predictions":
        render_predictions()
    elif page == "Knockout Bracket":
        render_knockout()
    elif page == "Fixtures":
        render_fixtures()


if __name__ == "__main__":
    main()
