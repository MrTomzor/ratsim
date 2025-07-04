using UnityEngine;

public class SemanticLidarSensor : MonoBehaviour
{
    public int angleStartDeg = 45; // Start angle in degrees
    public int angleEndDeg = 45;
    public int angleIncrementDeg = 5;
    public float maxRange = 100f; // Maximum range of the lidar sensor

    public uint descriptorDimension = 3;

    public string topicName = "/lidar2d";

    public bool debugDrawRays = false;

    int numRays;
    RoslikeTCPServer conn;

    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        numRays = 1 + (angleEndDeg - angleStartDeg) / angleIncrementDeg;

        conn = RoslikeTCPServer.GetInstance();
        conn.RegisterTimerDiscrete(SenseAndPublish, 1);
        //SenseAndPublish(null); 

    }

    public void SenseAndPublish(TimerEvent ev)
    {
        Lidar2DMessage msg = new Lidar2DMessage();

        msg.angleIncrementDeg = angleIncrementDeg;
        msg.angleStartDeg = angleStartDeg;
        msg.maxRange = maxRange;

        msg.ranges = new float[numRays];
        msg.descriptors = new float[numRays * descriptorDimension];

        // Cast rays in 2D starting from angleStartDeg to angleEndDeg
        int numhit = 0;
        for (int i = 0; i < numRays; i++)
        {
            float angle = angleStartDeg + i * angleIncrementDeg;
            float radians = angle * Mathf.Deg2Rad;

            // Cast a ray in the specified direction
            Vector3 dirvec = new Vector3(Mathf.Sin(radians), 0, Mathf.Cos(radians));
            dirvec = transform.TransformDirection(dirvec);
            RaycastHit hit;
            Physics.Raycast(transform.position, dirvec, out hit, maxRange);

            if (hit.collider != null)
            {
                msg.ranges[i] = hit.distance;
                numhit++;

                // Get the semantic object and its descriptor
                SemanticObject semanticObject = hit.collider.GetComponent<SemanticObject>();
                if (semanticObject != null)
                {
                    uint dim = semanticObject.GetDescriptorDimension();
                    for (uint j = 0; j < dim; j++)
                    {
                        msg.descriptors[i * dim + j] = semanticObject.GetDescriptor()[j];
                    }
                }
                else
                {
                    for (uint j = 0; j < descriptorDimension; j++)
                    {
                        msg.descriptors[i * descriptorDimension + j] = 0;
                    }
                }
            }
            else
            {
                msg.ranges[i] = -1;
                for (uint j = 0; j < descriptorDimension; j++)
                {
                    msg.descriptors[i * descriptorDimension + j] = 0;
                }
            }

            if (debugDrawRays)
            {
                Debug.DrawLine(transform.position, transform.position + dirvec * (msg.ranges[i] < 0 ? maxRange : msg.ranges[i]), Color.red, 0);

            }
        }
        if (debugDrawRays)
        {
            //Debug.Log("ranges: " + string.Join(", ", msg.ranges));
            //Debug.Log("num hits: " + numhit);
        
        }


        // Publish the message to the specified topic
        conn.Publish(topicName, msg);
    }
}
