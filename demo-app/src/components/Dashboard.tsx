import {
  archiveUserProfile,
  deleteUserProfile,
  listUserProfiles,
  loadUserProfile,
  renameUserProfile,
} from "../services/userService";

export async function Dashboard() {
  const profile = await loadUserProfile("demo-user");
  return `<h1>${profile.name}</h1>`;
}

export async function ProfilePanel() {
  const profile = await loadUserProfile("demo-user");
  return `<section>${profile.id}</section>`;
}

export async function UserList() {
  const profiles = await listUserProfiles();
  return profiles.map((profile) => profile.name).join(", ");
}

export async function UserCard() {
  const profile = await loadUserProfile("demo-user");
  return `<article>${profile.name}</article>`;
}

export async function UserEditor() {
  const profile = await renameUserProfile("demo-user", "Demo User");
  return `<form>${profile.name}</form>`;
}

export async function UserArchiveButton() {
  await archiveUserProfile("demo-user");
  return "Archived";
}

export async function UserDeleteButton() {
  await deleteUserProfile("demo-user");
  return "Deleted";
}

export async function UserSummary() {
  const profiles = await listUserProfiles();
  return `${profiles.length} users`;
}
