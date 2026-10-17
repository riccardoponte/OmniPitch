"""CLI utility to run and inspect the synthetic match event engine."""

import argparse
import json
import time
from omnipitch.generator.engine import MatchSimulationEngine


def main():
    parser = argparse.ArgumentParser(description="OmniPitch Synthetic Match Event Streamer")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic seed for simulation")
    parser.add_argument("--count", type=int, default=10, help="Number of events to generate")
    parser.add_argument("--stream", action="store_true", help="Stream events in real time with delay")
    parser.add_argument("--delay", type=float, default=0.5, help="Seconds between streamed events")

    args = parser.parse_args()

    engine = MatchSimulationEngine(seed=args.seed)
    print(f"--- OmniPitch Simulation Started ---")
    print(f"Match: {engine.home_team.name} vs {engine.away_team.name}")
    print(f"Seed: {args.seed} | Target Events: {args.count}\n")

    events = engine.generate_full_match(event_count=args.count)

    for evt in events:
        data = evt.model_dump()
        print(f"[{evt.minute:02d}:{evt.second:02d}] {evt.event_id} | {evt.event_type.value.upper()} by {evt.player.name if evt.player else 'N/A'} ({evt.team_id})")
        if evt.ball_speed_kmh:
            print(f"       Physics: Ball Speed: {evt.ball_speed_kmh} km/h | Pass Dist: {evt.pass_distance_m or 0}m | Diff: {evt.pass_difficulty_rating or 0}")
        print(f"       Tactics: Control: {evt.tactical_context.control_vs_chaos_index} | Press: {evt.tactical_context.defensive_pressure_index} | Tempo: {evt.tactical_context.game_rhythm_tempo}")

        if args.stream:
            time.sleep(args.delay)

    print("\n--- Match Simulation Complete ---")
    print(f"Final Score: {engine.home_team.name} {engine.score.home_score} - {engine.score.away_score} {engine.away_team.name}")


if __name__ == "__main__":
    main()
