import { loadUserProfile } from "../src/services/userService";

test("loads a user profile through the service boundary", async () => {
  await expect(loadUserProfile("demo-user")).resolves.toEqual({
    id: "demo-user",
    name: "Demo User",
  });
});

