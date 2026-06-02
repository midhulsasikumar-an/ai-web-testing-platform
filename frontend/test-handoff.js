// Simple standalone test script to verify our regex and payload logic

function assertEqual(actual, expected, name) {
  if (actual === expected) {
    console.log(`✅ PASS: ${name}`);
  } else {
    console.error(`❌ FAIL: ${name} (Expected '${expected}', got '${actual}')`);
  }
}

function extractUrl(prompt, instruction) {
  const URL_REGEX = /https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)/gi;
  let url = "";
  
  const promptMatch = prompt.match(URL_REGEX);
  if (promptMatch && promptMatch.length > 0) {
    url = promptMatch[0];
  } else {
    const instructionMatch = instruction.match(URL_REGEX);
    if (instructionMatch && instructionMatch.length > 0) {
      url = instructionMatch[0];
    }
  }
  return url;
}

function isPayloadStale(createdAtISO) {
  const now = new Date().getTime();
  const createdTime = new Date(createdAtISO).getTime();
  if (!isNaN(createdTime) && (now - createdTime) < 10 * 60 * 1000) {
    return false;
  }
  return true;
}

console.log("--- Testing URL Extraction ---");
assertEqual(
  extractUrl("I need to test https://www.saucedemo.com", "Here are the instructions."),
  "https://www.saucedemo.com",
  "Extracts from prompt"
);

assertEqual(
  extractUrl("No url here", "Generate test for http://example.com/login"),
  "http://example.com/login",
  "Extracts from instruction if prompt has no URL"
);

assertEqual(
  extractUrl("I want to test https://my-app.vercel.app/dashboard?user=1", "Test plan generated."),
  "https://my-app.vercel.app/dashboard?user=1",
  "Extracts complex URLs with query params"
);

console.log("\n--- Testing Stale Payload Logic ---");

const justNow = new Date().toISOString();
assertEqual(isPayloadStale(justNow), false, "Fresh payload is NOT stale");

const fiveMinsAgo = new Date(new Date().getTime() - 5 * 60 * 1000).toISOString();
assertEqual(isPayloadStale(fiveMinsAgo), false, "5 min old payload is NOT stale");

const fifteenMinsAgo = new Date(new Date().getTime() - 15 * 60 * 1000).toISOString();
assertEqual(isPayloadStale(fifteenMinsAgo), true, "15 min old payload IS stale");

const malformedDate = "not-a-date";
assertEqual(isPayloadStale(malformedDate), true, "Malformed date IS stale");

console.log("\nAll verification tests completed.");
