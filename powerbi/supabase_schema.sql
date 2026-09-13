-- Supabase schema for the F1 star schema.
-- Run this once in: Supabase > SQL Editor > New query

create table if not exists public.races (
    season        int not null,
    round_number  int not null,
    name          text not null,
    official_name text,
    country       text,
    location      text,
    event_date    date,
    total_laps    int,
    primary key (season, round_number)
);

create table if not exists public.drivers (
    season         int not null,
    driver_code    text not null,
    driver_number  int,
    full_name      text,
    team           text,
    primary key (season, driver_code)
);

create table if not exists public.laps (
    race_season       int not null,
    race_round        int not null,
    driver_code       text not null,
    driver_number     int,
    team              text,
    lap_number        int not null,
    lap_time_seconds  double precision,
    compound          text,
    tyre_life         int,
    track_status      text,
    pit_in_time       double precision,
    pit_out_time      double precision,
    is_personal_best  boolean,
    stint             int,
    primary key (race_season, race_round, driver_code, lap_number)
);

create index if not exists idx_laps_race on public.laps (race_season, race_round);
create index if not exists idx_laps_driver on public.laps (driver_code);
create index if not exists idx_drivers_season on public.drivers (season);