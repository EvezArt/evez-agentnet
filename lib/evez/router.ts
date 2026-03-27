export function routeLane(lane: string) {
  switch (lane) {
    case "command":
      return "#00-command";
    case "digest":
      return "#evez-autonomous-core";
    case "alerts":
      return "#02-runtime-alerts";
    case "research":
      return "#04-research";
    case "integrations":
      return "#08-integrations";
    default:
      return "#unknown";
  }
}
