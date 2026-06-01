type User = {
  id: string;
  name: string;
};

const USERS: Record<string, User> = {
  "demo-user": { id: "demo-user", name: "Demo User" },
};

export async function getUserById(userId: string): Promise<User> {
  return USERS[userId] ?? { id: userId, name: "Unknown User" };
}

export async function findUsers(): Promise<User[]> {
  return Object.values(USERS);
}

export async function saveUser(user: User): Promise<User> {
  USERS[user.id] = user;
  return user;
}

export async function archiveUser(userId: string): Promise<void> {
  delete USERS[userId];
}

export async function deleteUser(userId: string): Promise<void> {
  delete USERS[userId];
}
