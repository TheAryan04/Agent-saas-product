export const SEED_PROJECT = {
  title: "Orbit — Ship better, together",
  aspectRatio: "16:9",
  brand: { name: "Orbit", primaryColor: "#7CFFCB", accentColor: "#55D6FF", background: "#0B1016", font: "Outfit" },
  scenes: [
    { template: "TextReveal", durationSec: 2.5, props: { headline: "Ship better, together", eyebrow: "ORBIT WORKSPACE", subline: "A calm home for product teams.", transition: "fade", motion: "rise" } },
    { template: "Flowchart", durationSec: 3, props: { headline: "From idea to impact", steps: ["Plan", "Build", "Launch"], transition: "slide", motion: "pop" } },
    { template: "DeviceMockup", durationSec: 3, props: { headline: "One calm command center", label: "orbit.app / workspace", transition: "zoom", motion: "drift" } },
    { template: "CallToAction", durationSec: 2.5, props: { headline: "Make momentum visible", button: "Start your next sprint", transition: "wipe", motion: "pop" } },
  ],
};
