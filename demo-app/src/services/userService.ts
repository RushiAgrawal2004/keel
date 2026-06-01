import {
  archiveUser,
  deleteUser,
  findUsers,
  getUserById,
  saveUser,
} from "../db/users";

export async function loadUserProfile(userId: string) {
  const user = await getUserById(userId);
  return {
    id: user.id,
    name: user.name,
  };
}

export async function listUserProfiles() {
  return findUsers();
}

export async function renameUserProfile(userId: string, name: string) {
  return saveUser({ id: userId, name });
}

export async function archiveUserProfile(userId: string) {
  return archiveUser(userId);
}

export async function deleteUserProfile(userId: string) {
  return deleteUser(userId);
}
