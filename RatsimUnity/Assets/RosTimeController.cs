using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using System;
//using Unity.Robotics.ROSTCPConnector.
using RosMessageTypes.Std;
//using RosMessageTypes.Sensor;
using Unity.VisualScripting;


public class RosTimeController : MonoBehaviour
{
    
    public bool paused = true;
    public bool stepModeEnabled = true;
    /*public float currentRewardSum = 0;

    public static void ApplyReward(float r)
    {
        instance.currentRewardSum += r;
    }*/

    /*public bool episodeDone = false;
    public static void EndEpisode()
    {
        instance.episodeDone = true;
    }*/

    public delegate void OnGlobalSensorsRequest();
    public static OnGlobalSensorsRequest onGlobalSensorsRequest;


    public static bool IsPaused()
    {
        if (instance == null || instance.paused)
        {
            return true;
        }
        return false;
    }
    

    static RosTimeController instance;
    public static bool AsyncSensingAllowed()
    {
        if (instance == null || instance.stepModeEnabled)
        {
            return false;
        }
        return true;
    }

    public String step_topic_name = "/step";
    public String step_end_topic_name = "/step_finished";
    //public String episodeStateTopicName = "/episode_done";
    //public String rewardTopicName = "/reward";
    

    public float maxTimeScale = 200;

    public int numSteps = 0;
    public int numFixedUpdates = 0;
    public int numFixedUpdatesLastStep = 0;

    public int numFixedUpdatesPerGymStep = 5;

    // Start is called before the first frame update
    void Start()
    {
        /* m_ROS = ROSConnection.GetOrCreateInstance(); */
        //ROSConnection.GetOrCreateInstance().Unsubscribe(topic_name);
        ROSConnection.GetOrCreateInstance().Subscribe<EmptyMsg>(step_topic_name, StepTime);
        ROSConnection.GetOrCreateInstance().RegisterPublisher<EmptyMsg>(step_end_topic_name);
        //ROSConnection.GetOrCreateInstance().RegisterPublisher<BoolMsg>(episodeStateTopicName);
        //ROSConnection.GetOrCreateInstance().RegisterPublisher<Float64Msg>(rewardTopicName);
        instance = this;
    }

    // Update is called once per frame
    void Update()
    {
        if (Time.deltaTime > 0)
        {
            Debug.Log("Nonzero DT Update");
        }
        //Debug.Log("Normal Update, DT: " + Time.deltaTime);
    }

    public void StepTime(EmptyMsg msg)
    {
        Debug.Log("-------STEP! Game time is: " + Time.time);
        //Time.fixedDeltaTime = 0.2f;
        Time.timeScale = maxTimeScale;
        //Time.fixedDeltaTime = 0.02f * Time.timeScale;
        paused = false;
        Debug.Log("----- num fixed updates since last step: " + (numFixedUpdates - numFixedUpdatesLastStep));

        //numFixedUpdatesLastStep = numFixedUpdates;
    }

    void FixedUpdate()
    {
        
        Time.timeScale = 0;
        paused = true;
        numFixedUpdates += 1;
        //Debug.Log("Fixed index: " + numFixedUpdates);
        Debug.Log("FIXED! Game time is: " + Time.time + " Index: " + numFixedUpdates);

        if (numFixedUpdates - numFixedUpdatesLastStep == numFixedUpdatesPerGymStep)
        {
            
            // INVOKE SENSORS
            Debug.Log("PERFORMING SENSING FOR GYM STEP! Time: " + Time.time);
            onGlobalSensorsRequest?.Invoke();
            numFixedUpdatesLastStep = numFixedUpdates;
            //ROSConnection.GetOrCreateInstance().Publish(episodeStateTopicName, new BoolMsg(episodeDone));


            // PUBLISH REWARD!
            // TODO - implement reward HIGHER UP!!! (not here, but in Env config! here just world mechanisms!)
            //ROSConnection.GetOrCreateInstance().Publish(rewardTopicName, new Float64Msg(currentRewardSum));
            //currentRewardSum = 0;

            // SIGNIFY STEP END!
            ROSConnection.GetOrCreateInstance().Publish(step_end_topic_name, new EmptyMsg());
        }

    }
}
