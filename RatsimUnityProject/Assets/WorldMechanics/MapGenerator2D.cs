using UnityEngine;

public class MapGenerator2D : MonoBehaviour
{
    public string topicName = "/mapgen";
    public float obstacleHeight = 1.0f; // Height of the obstacles in Unity units
    public GameObject obstaclePrefab; // Prefab to instantiate for obstacles

    int width, height;
    float meters_per_pixel;

    Vector3 mapPixelToWorldPos(int x, int y)
    {
        return new Vector3((x - width/2.0f) * meters_per_pixel, 0, -(y - height/2.0f) * meters_per_pixel);
    }

    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        var conn = RoslikeTCPServer.GetInstance();
        conn.Subscribe<MapGenTemplate2D>(topicName, GenerateMap);
    }


    public void GenerateMap(MapGenTemplate2D msg)
    {
        Debug.Log("Received MapGenTemplate2D message");
        Debug.Log($"Map size: {msg.width}x{msg.height}, meters per pixel: {msg.meters_per_pixel}");
        width = msg.width;
        height = msg.height;
        meters_per_pixel = msg.meters_per_pixel;

        // Utility function to reshape a flattened mask into 2D bool array
        bool[,] ReshapeMask(int[] flatMask, int width, int height)
        {
            bool[,] mask2D = new bool[height, width];
            for (int y = 0; y < height; y++)
            {
                for (int x = 0; x < width; x++)
                {
                    mask2D[y, x] = flatMask[y * width + x] != 0;
                }
            }
            return mask2D;
        }

        // Reshape all masks
        bool[,] obstacles = ReshapeMask(msg.obstacles, msg.width, msg.height);
        bool[,] spawnMask = ReshapeMask(msg.spawnMask, msg.width, msg.height);
        bool[,] poiMask = ReshapeMask(msg.poiMask, msg.width, msg.height);
        bool[,] forbiddenMask = ReshapeMask(msg.forbiddenMask, msg.width, msg.height);
        bool[,] growableMask = ReshapeMask(msg.growableMask, msg.width, msg.height);

        // Example: visualize masks in console (optional)
        Debug.Log($"Map size: {msg.width}x{msg.height}, meters per pixel: {msg.meters_per_pixel}");
        Debug.Log($"Obstacles: {CountTrue(obstacles)}, Spawn: {CountTrue(spawnMask)}, POIs: {CountTrue(poiMask)}");
        

        SpawnObstacles(obstacles, msg.meters_per_pixel);
    }

    public void SpawnObstacles(bool[,] obstacleMask, float metersPerPixel)
    {
        int height = obstacleMask.GetLength(0);
        int width = obstacleMask.GetLength(1);

        for (int y = 0; y < height; y++)
        {
            for (int x = 0; x < width; x++)
            {
                if (obstacleMask[y, x])
                {
                    // Calculate world position
                    //float worldX = x * metersPerPixel;
                    //float worldY = y * metersPerPixel;
                    Vector3 worldPos = mapPixelToWorldPos(x, y);
                    float worldX = worldPos.x;
                    float worldY = worldPos.z;

                    // Instantiate an obstacle prefab at (worldX, worldY)
                    // Scale by metersPerPixel if needed
                    GameObject obstacle = Instantiate(obstaclePrefab, new Vector3(worldX, 0, worldY), Quaternion.identity);
                    float scale = metersPerPixel; // Adjust scale as needed
                    obstacle.transform.localScale = new Vector3(scale, obstacleHeight, scale);
                    obstacle.transform.parent = this.transform; // Parent to this GameObject for organization
                }
            }
        }
    }

    // Helper to count true values in 2D bool array
    int CountTrue(bool[,] mask)
    {
        int count = 0;
        foreach (var val in mask)
        {
            if (val) count++;
        }
        return count;
    }
}
