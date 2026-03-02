import client from './client'
import type { Category, CategoryGroup, CategoryGroupWithCategories } from './types'

/** List all category groups (each group includes its categories). */
export async function listCategoryGroups(): Promise<CategoryGroupWithCategories[]> {
  const { data } = await client.get<CategoryGroupWithCategories[]>('/api/category-groups')
  return data
}

export async function createCategoryGroup(
  name: string,
  sort_order: number = 0,
): Promise<CategoryGroup> {
  const { data } = await client.post<CategoryGroup>('/api/category-groups', { name, sort_order })
  return data
}

export async function deleteCategoryGroup(id: number): Promise<void> {
  await client.delete(`/api/category-groups/${id}`)
}

export async function createCategory(
  group_id: number,
  name: string,
  sort_order: number = 0,
): Promise<Category> {
  const { data } = await client.post<Category>('/api/categories', { group_id, name, sort_order })
  return data
}

export async function updateCategory(
  id: number,
  payload: Partial<Pick<Category, 'name' | 'sort_order' | 'hidden'>>,
): Promise<Category> {
  const { data } = await client.patch<Category>(`/api/categories/${id}`, payload)
  return data
}

export async function deleteCategory(id: number): Promise<void> {
  await client.delete(`/api/categories/${id}`)
}

/** Returns category groups with their categories nested (single API request). */
export async function listGroupsWithCategories(): Promise<CategoryGroupWithCategories[]> {
  return listCategoryGroups()
}
